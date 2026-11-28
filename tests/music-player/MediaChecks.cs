using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using SaberTrials.Music;
using Windows.Media;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Storage;

internal static class MediaChecks
{
    private static void Check(bool condition, string label)
    {
        if (!condition) throw new InvalidOperationException(label);
        Console.WriteLine("PASS " + label);
    }

    private static void WriteSilentWav(string path, int seconds)
    {
        const int samplesPerSecond = 8000;
        const short bytesPerSample = 2;
        int size = samplesPerSecond * bytesPerSample * seconds;
        using (var writer = new BinaryWriter(File.Create(path)))
        {
            writer.Write(Encoding.ASCII.GetBytes("RIFF"));
            writer.Write(36 + size);
            writer.Write(Encoding.ASCII.GetBytes("WAVEfmt "));
            writer.Write(16);
            writer.Write((short)1); // PCM
            writer.Write((short)1); // mono
            writer.Write(samplesPerSecond);
            writer.Write(samplesPerSecond * bytesPerSample);
            writer.Write(bytesPerSample);
            writer.Write((short)(bytesPerSample * 8));
            writer.Write(Encoding.ASCII.GetBytes("data"));
            writer.Write(size);
            writer.Write(new byte[size]);
        }
    }

    private static async Task WaitFor(MusicModel model, Func<bool> condition, string label)
    {
        DateTime limit = DateTime.UtcNow.AddSeconds(15);
        while (!condition() && DateTime.UtcNow < limit)
        {
            await Task.Delay(100);
            await model.RefreshAsync();
        }
        if (!condition()) throw new TimeoutException(label + " (" + model.Status + ")");
        Check(true, label);
    }

    private static async Task CheckLocal(string directory, string preferences, MusicModel model)
    {
        string moon = Path.Combine(directory, "Quiet Moon.wav");
        string sun = Path.Combine(directory, "Quiet Sun.wav");
        WriteSilentWav(moon, 5);
        WriteSilentWav(sun, 4);
        Check(model.Source == "Local" && !model.CanToggle && model.TrackIndex == -1, "initial empty library");
        await model.CommandAsync("volume", "65");
        await model.CommandAsync("volume", "-5");
        Check(model.Volume == 60 && new MusicModel(preferences).Volume == 60, "local volume supports absolute and relative changes and persists");
        model.AddFiles(new[] { moon, sun, moon, Path.Combine(directory, "missing.mp3") });
        Check(model.Tracks.Count == 2 && model.TrackIndex == 0 && !model.Playing && model.CanToggle,
            "import filters missing and duplicate files");
        await model.CommandAsync("search", "quiet");
        Check(model.Status.StartsWith("Several") && !model.Playing, "ambiguous title requires a choice");
        await model.CommandAsync("playquery", "quiet moon");
        await WaitFor(model, () => model.Playing && model.CanSeek && model.Position > 0.15, "WPF plays the named PCM file");
        Check(Math.Abs(model.Duration - 5) < 0.1 && model.CanNext && !model.CanPrevious, "local duration and transport controls");
        await model.CommandAsync("pause", "");
        Check(!model.Playing, "pause local audio");
        await model.CommandAsync("seek", "2.5");
        Check(Math.Abs(model.Position - 2.5) < 0.25, "seek paused audio");
        await model.CommandAsync("toggle", "");
        await WaitFor(model, () => model.Playing && model.Position > 2.55, "resume from seek");
        await model.CommandAsync("next", "");
        await WaitFor(model, () => model.TrackIndex == 1 && model.Playing, "skip local track");
        await model.CommandAsync("previous", "");
        await WaitFor(model, () => model.TrackIndex == 0 && model.Playing, "previous local track");
        await model.CommandAsync("seek", "4.8");
        await WaitFor(model, () => model.TrackIndex == 1 && model.Playing, "auto-advance on completion");
        await model.CommandAsync("source", "YouTube Music");
        var restored = new MusicModel(preferences);
        Check(restored.Source == model.Source && restored.Tracks.SequenceEqual(model.Tracks) && restored.TrackIndex == 1,
            "restore source, ordered library and selection");
        await model.CommandAsync("source", "Local");
        Check(!model.Playing && model.Title == "Quiet Sun", "switching sources pauses local audio");
        await model.CommandAsync("track", "0");
        await WaitFor(model, () => model.Playing && model.TrackIndex == 0, "select a local library entry");
        await model.CommandAsync("pause", "");
    }

    private static MediaPlaybackItem MakeItem(StorageFile file, string title, StorageFile cover = null)
    {
        var item = new MediaPlaybackItem(MediaSource.CreateFromStorageFile(file));
        var display = item.GetDisplayProperties();
        display.Type = MediaPlaybackType.Music;
        display.MusicProperties.Title = title;
        display.MusicProperties.Artist = "Saber Trials test provider";
        if (cover != null) display.Thumbnail = Windows.Storage.Streams.RandomAccessStreamReference.CreateFromFile(cover);
        item.ApplyDisplayProperties(display);
        return item;
    }

    private static async Task CheckWindowsMedia(string directory, MusicModel model)
    {
        string path = Path.Combine(directory, "Silent provider.wav");
        WriteSilentWav(path, 45);
        var file = await StorageFile.GetFileFromPathAsync(path);
        string marker = "Saber Trials test " + Guid.NewGuid().ToString("N");
        var playlist = new MediaPlaybackList();
        string coverPath = Path.Combine(directory, "cover.bmp");
        using (var bmp = new BinaryWriter(File.Create(coverPath)))
        {
            bmp.Write((ushort)0x4d42); bmp.Write(58); bmp.Write(0); bmp.Write(54);
            bmp.Write(40); bmp.Write(1); bmp.Write(1); bmp.Write((ushort)1); bmp.Write((ushort)24);
            bmp.Write(new byte[24]); bmp.Write(new byte[]{30,80,210,0});
        }
        playlist.Items.Add(MakeItem(file, marker, await StorageFile.GetFileFromPathAsync(coverPath)));
        playlist.Items.Add(MakeItem(file, marker + " next"));
        await model.CommandAsync("source", "YouTube Music");
        using (var provider = new MediaPlayer { Volume = 0, Source = playlist })
        {
            provider.Play();
            await WaitFor(model, () => model.Sessions.Any(x => x.Contains(marker)), "Windows publishes the unique test session");
            Check(model.SessionIndex == -1 && !model.CanToggle, "generic Windows session starts unlinked");
            await model.CommandAsync("toggle", "");
            Check(model.Status.Contains("Choose an active") && provider.PlaybackSession.PlaybackState == MediaPlaybackState.Playing,
                "unlinked transport cannot take over the test session");
            // Select only the session with this run's marker. Other media sessions may belong to the user.
            int index = model.Sessions.ToList().FindIndex(x => x.Contains(marker));
            await model.CommandAsync("session", index.ToString());
            await WaitFor(model, () => model.Title == marker && model.Playing, "explicit session selection reads provider playback");
            Check(model.Artist == "Saber Trials test provider" && model.Duration >= 40, "provider metadata and timeline");
            await WaitFor(model, () => model.Artwork.Image != null, "the selected media session publishes cover art");
            string testApp = System.Diagnostics.Process.GetCurrentProcess().ProcessName + ".exe";
            int initialVolume = await Task.Run(() => AppVolume.ReadOrSet(testApp));
            Check(initialVolume >= 0, "Windows identifies the test player's own mixer session");
            try
            {
                await Task.Run(() => AppVolume.ReadOrSet(testApp, 37));
                Check(await Task.Run(() => AppVolume.ReadOrSet(testApp)) == 37, "the app mixer reads back the new absolute volume");
                await Task.Run(() => AppVolume.ReadOrSet(testApp, -5, true));
                Check(await Task.Run(() => AppVolume.ReadOrSet(testApp)) == 32, "the app mixer applies a relative volume change");
                Check(await Task.Run(() => AppVolume.ReadOrSet("SaberTrials-Nobody.exe", 10)) == -1, "an unmatched player cannot change another app's volume");
            }
            finally { await Task.Run(() => AppVolume.ReadOrSet(testApp, initialVolume)); }
            string token = model.Artwork.GameToken();
            using (var map = System.IO.MemoryMappedFiles.MemoryMappedFile.OpenExisting(@"Local\SaberTrials.Music.Cover." + token))
            using (var view = map.CreateViewAccessor(0, 4, System.IO.MemoryMappedFiles.MemoryMappedFileAccess.Read))
                Check(view.ReadByte(0) == 210 && view.ReadByte(1) == 80 && view.ReadByte(2) == 30 && view.ReadByte(3) == 255,
                    "the game receives the matching RGBA artwork");
            Check(model.CanToggle && model.CanSeek, "provider play/pause and seek capabilities");
            await model.CommandAsync("pause", "", "Spotify");
            Check(provider.PlaybackSession.PlaybackState == MediaPlaybackState.Playing && model.Status.Contains("source changed"),
                "a queued provider command cannot operate on a different source");
            await model.CommandAsync("pause", "");
            await WaitFor(model, () => !model.Playing && provider.PlaybackSession.PlaybackState == MediaPlaybackState.Paused,
                "pause selected provider");
            await model.CommandAsync("play", "");
            await WaitFor(model, () => model.Playing && provider.PlaybackSession.PlaybackState == MediaPlaybackState.Playing,
                "resume selected provider");
            await model.CommandAsync("seek", "15");
            await WaitFor(model, () => provider.PlaybackSession.Position.TotalSeconds >= 14, "seek selected provider");
            Check(model.CanNext, "provider exposes next track");
            await model.CommandAsync("next", "");
            await WaitFor(model, () => model.Title == marker + " next" && playlist.CurrentItemIndex == 1, "next provider track");
            await WaitFor(model, () => model.Artwork.Image == null && model.Artwork.GameToken() == "-", "a track without art clears the old cover");
            Check(model.CanPrevious, "provider exposes previous track");
            await model.CommandAsync("previous", "");
            await WaitFor(model, () => model.Title == marker && playlist.CurrentItemIndex == 0, "previous provider track");
        }
        await WaitFor(model, () => model.SessionIndex == -1 && !model.CanToggle, "closed provider disconnects");
        using (var replacement = new MediaPlayer { Volume = 0, Source = MakeItem(file, marker + " replacement") })
        {
            replacement.Play();
            await WaitFor(model, () => model.Sessions.Any(x => x.Contains(marker + " replacement")), "replacement session appears");
            Check(model.SessionIndex == -1 && !model.CanToggle, "same-app replacement requires an explicit choice");
        }
    }

    [STAThread]
    public static int Main(string[] args)
    {
        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        int code = 0;
        app.Startup += async (s, e) =>
        {
            try
            {
                string preferences = Path.Combine(args[0], "library.txt");
                var model = new MusicModel(preferences);
                await CheckLocal(args[0], preferences, model);
                await CheckWindowsMedia(args[0], model);
            }
            catch (Exception ex) { Console.Error.WriteLine(ex); code = 1; }
            finally { app.Shutdown(); }
        };
        app.Run();
        return code;
    }
}
