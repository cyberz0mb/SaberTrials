using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;

namespace SaberTrials.Music
{
    internal static class PlayerHost
    {
        internal static readonly string Endpoint = MakeEndpoint();
        private static Application app;
        private static MainWindow window;
        private static MusicModel model;
        private static DispatcherTimer timer;
        private static bool refreshing, closing, launchingFromGame;
        private static Process game;
        private static string bridgeError = "";
        private static readonly CancellationTokenSource quit = new CancellationTokenSource();

        private static string MakeEndpoint()
        {
            string dir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
            uint hash = 2166136261;
            foreach (char ch in dir)
                hash = unchecked((hash ^ (uint)(ch >= 'a' && ch <= 'z' ? ch - 32 : ch)) * 16777619);
            return "SaberTrials.Music." + Process.GetCurrentProcess().SessionId + "." + hash.ToString("x8");
        }

        [STAThread]
        public static int Main(string[] args)
        {
            int pid;
            launchingFromGame = args.Length == 2 && args[0] == "--game" && int.TryParse(args[1], out pid);
            if (launchingFromGame) AttachGame(int.Parse(args[1], CultureInfo.InvariantCulture));
            bool first;
            using (var instance = new Mutex(true, @"Local\" + Endpoint, out first))
            {
                if (!first)
                {
                    if (!launchingFromGame) ActivateExisting();
                    return 0;
                }
                try
                {
                    app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
                    string library = Environment.GetEnvironmentVariable("SABERTRIALS_MUSIC_LIBRARY");
                    model = string.IsNullOrWhiteSpace(library) ? new MusicModel() : new MusicModel(Path.GetFullPath(library));
                    window = new MainWindow(model);
                    window.Closing += (sender, e) =>
                    {
                        if (!closing && GameRunning())
                        {
                            e.Cancel = true;
                            window.Hide();
                        }
                        else Stop();
                    };
                    app.Dispatcher.BeginInvoke(new Action(() => { _ = ServeAsync(); }));
                    timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(550) };
                    timer.Tick += async (s, e) => await UpdateAsync();
                    timer.Start();
                    if (!launchingFromGame) window.Show();
                    app.Run();
                    quit.Cancel();
                    return 0;
                }
                finally { instance.ReleaseMutex(); }
            }
        }

        private static void AttachGame(int pid)
        {
            try
            {
                var candidate = Process.GetProcessById(pid);
                if (candidate.SessionId != Process.GetCurrentProcess().SessionId) { candidate.Dispose(); return; }
                if (game != null) game.Dispose();
                game = candidate;
            }
            catch (ArgumentException) { }
        }

        private static bool GameRunning()
        {
            if (game != null && !game.HasExited) return true;
            // A desktop-first launch can attach when the player boots the game later.
            foreach (var p in Process.GetProcessesByName("SaberTrials.x86_64"))
            {
                try
                {
                    if (p.SessionId == Process.GetCurrentProcess().SessionId &&
                        string.Equals(Path.GetDirectoryName(p.MainModule.FileName), AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
                    { AttachGame(p.Id); return true; }
                }
                catch (Exception e) when (e is InvalidOperationException || e is System.ComponentModel.Win32Exception) { }
                finally { p.Dispose(); }
            }
            return false;
        }

        private static void Stop()
        {
            if (closing) return;
            closing = true;
            timer?.Stop();
            quit.Cancel();
            app.Dispatcher.BeginInvoke(new Action(app.Shutdown));
        }

        private static async Task UpdateAsync()
        {
            if (refreshing || closing) return;
            refreshing = true;
            try
            {
                if (window.IsVisible)
                {
                    await model.RefreshAsync();
                    if (!closing && window.IsVisible) window.Sync();
                }
                else if (!GameRunning()) Stop();
            }
            catch (Exception e) { bridgeError = e.Message; }
            finally { refreshing = false; }
        }

        private static void ShowDesktop()
        {
            if (!window.IsVisible) window.Show();
            if (window.WindowState == WindowState.Minimized) window.WindowState = WindowState.Normal;
            window.Activate();
            window.Sync();
        }

        private static void ActivateExisting()
        {
            try
            {
                using (var pipe = new NamedPipeClientStream(".", Endpoint, PipeDirection.InOut))
                {
                    pipe.Connect(1600);
                    var buf = Encoding.UTF8.GetBytes("desktop\t\t\n");
                    pipe.Write(buf, 0, buf.Length);
                    pipe.Flush();
                }
            }
            catch (IOException) { }
            catch (TimeoutException) { }
        }

        private static async Task ServeAsync()
        {
            var acl = new PipeSecurity();
            acl.SetAccessRuleProtection(true, false);
            acl.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.NetworkSid, null), PipeAccessRights.FullControl, AccessControlType.Deny));
            acl.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User, PipeAccessRights.FullControl, AccessControlType.Allow));
            while (!quit.IsCancellationRequested)
            {
                try
                {
                    using (var pipe = new NamedPipeServerStream(Endpoint, PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
                               PipeOptions.Asynchronous, 8192, 4096, acl))
                    {
                        await pipe.WaitForConnectionAsync(quit.Token);
                        using (var deadline = CancellationTokenSource.CreateLinkedTokenSource(quit.Token))
                        {
                            deadline.CancelAfter(2500);
                            var bytes = new byte[2048];
                            int used = 0;
                            while (used < bytes.Length)
                            {
                                int n = await pipe.ReadAsync(bytes, used, bytes.Length - used, deadline.Token);
                                if (n == 0) break;
                                used += n;
                                if (bytes[used-1] == 10) break;
                            }
                            if (used == 0 || bytes[used-1] != 10) continue;
                            var input = Encoding.UTF8.GetString(bytes,0,used-1).Split('\t');
                            if (input.Length != 3 || input.Any(s => s.Any(char.IsControl))) continue;
                            // Resume on the WPF dispatcher. It also owns the local audio player.
                            string reply = await HandleAsync(input[0],input[1],input[2]);
                            if ((input[0] == "refresh" && input[2] == "cover1") || input[0] == "volume")
                                reply += "\t" + model.Artwork.GameToken() + "\t" + model.Volume.ToString(CultureInfo.InvariantCulture) + "\t" + model.VolumeLabel;
                            var output = Encoding.UTF8.GetBytes(reply + "\n");
                            await pipe.WriteAsync(output, 0, output.Length, quit.Token);
                        }
                    }
                }
                catch (OperationCanceledException) { }
                catch (IOException) { }
                catch (Exception e)
                {
                    bridgeError = e.Message;
                    if (!quit.IsCancellationRequested) await Task.Delay(250);
                }
            }
        }

        private static string Field(string s)
        {
            return new string((s ?? "").Where(c => !char.IsControl(c)).Take(170).ToArray());
        }

        private static async Task<string> HandleAsync(string verb, string source, string arg)
        {
            try
            {
                if (verb == "desktop") ShowDesktop();
                else if (verb == "attach")
                {
                    int pid;
                    if (int.TryParse(arg, out pid)) AttachGame(pid);
                }
                else if (verb == "refresh") await model.RefreshAsync();
                else
                {
                    bridgeError = "";
                    if (source.Length > 0 && model.Source != source) await model.CommandAsync("source", source);
                    else if (model.Source != "Local" && (verb == "play" || verb == "pause" || verb == "next" || verb == "previous" || verb == "toggle" || verb == "volume"))
                        await model.RefreshAsync();
                    if (verb == "cycle")
                    {
                        string[] choices = {"Local", "Spotify", "Apple Music", "YouTube Music"};
                        await model.CommandAsync("source", choices[(Array.IndexOf(choices, model.Source)+1)%choices.Length]);
                    }
                    else if (verb == "open" && model.Source == "Local")
                    {
                        // Let the user pick files in the desktop window they explicitly opened.
                        ShowDesktop();
                        _ = app.Dispatcher.BeginInvoke(new Action(async () =>
                        {
                            await model.CommandAsync("open", "", "Local");
                            if (!closing) window.Sync();
                        }));
                    }
                    else if (new[]{"toggle","play","pause","previous","next","source","search","playquery","open","volume"}.Contains(verb))
                    {
                        await model.CommandAsync(verb,arg,source);
                        if ((verb == "search" || verb == "playquery") && model.Source == "Local" && model.ChooseSearchResult)
                        {
                            ShowDesktop();
                            window.FilterLibrary(arg);
                        }
                    }
                    else bridgeError = "Unknown player command.";
                }
                if (window.IsVisible) window.Sync();
            }
            catch (Exception e) { bridgeError = e.Message; }
            return string.Join("\t", new[]{model.Source, model.Title, model.Artist,
                string.IsNullOrEmpty(bridgeError) ? model.Status : bridgeError,
                model.Playing ? "1":"0",model.CanToggle ? "1":"0",model.CanPrevious ? "1":"0",model.CanNext ? "1":"0",
                ((int)model.Position).ToString(CultureInfo.InvariantCulture), ((int)model.Duration).ToString(CultureInfo.InvariantCulture)}.Select(Field));
        }
    }
}
