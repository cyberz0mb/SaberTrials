using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media;
using Microsoft.Win32;
using Windows.Media.Control;
using Session = Windows.Media.Control.GlobalSystemMediaTransportControlsSession;
using PlaybackStatus = Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus;

namespace SaberTrials.Music
{
    public sealed class MusicModel
    {
        private static readonly string[] Sources = { "Local", "Spotify", "Apple Music", "YouTube Music" };
        private readonly List<string> files = new List<string>();
        internal TrackArtwork Artwork { get; } = new TrackArtwork();
        private readonly ConcurrentDictionary<string, string[]> tags = new ConcurrentDictionary<string, string[]>(StringComparer.OrdinalIgnoreCase);
        private Task indexing = Task.CompletedTask;
        internal int IndexedTracks { get { return tags.Count; } }
        internal bool ChooseSearchResult { get; private set; }
        private int localVolume = 50;
        private DateTime volumeRefresh;
        private Session volumeSession;
        public int Volume { get; private set; } = -1;
        public string VolumeLabel { get { return Source == "Local" ? "Volume" :
            AppVolume.Browser(selected?.SourceAppUserModelId) != null ? "Browser volume" : "App volume"; } }
        private readonly string settingsFile;
        private readonly SemaphoreSlim operations = new SemaphoreSlim(1, 1);
        private MediaPlayer player;
        private bool localOpened;
        private bool localWantsPlay;
        private string localError;
        private GlobalSystemMediaTransportControlsSessionManager manager;
        private List<Session> available = new List<Session>();
        private Session selected;
        private bool explicitSelection;
        private readonly Dictionary<Session, string> captions = new Dictionary<Session, string>();
        private DateTime captionRefresh;
        private DateTime retryAfter;
        private string remoteError;
        private string notice;
        private DateTime noticeUntil;
        private string state;

        public string Source { get; private set; } = "Local";
        public string Title { get; private set; } = "";
        public string Artist { get; private set; } = "";
        public string Status { get { return DateTime.UtcNow < noticeUntil ? notice : state ?? ""; } }
        public bool Playing { get; private set; }
        public bool CanToggle { get; private set; }
        public bool CanPrevious { get; private set; }
        public bool CanNext { get; private set; }
        public bool CanSeek { get; private set; }
        public double Position { get; private set; }
        public double Duration { get; private set; }
        public IReadOnlyList<string> Tracks { get; private set; } = new string[0];
        public IReadOnlyList<string> Sessions { get; private set; } = new string[0];
        public int TrackIndex { get; private set; } = -1;
        public int SessionIndex { get { return available.IndexOf(selected); } }

        public MusicModel() : this(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "SaberTrials", "MusicPlayer", "library.txt")) { }

        internal MusicModel(string settingsFile)
        {
            this.settingsFile = settingsFile;
            LoadSettings();
            UpdateTracks();
            if (Source == "Local") UpdateLocal();
            else ClearRemote();
        }

        private static string DisplayText(string value)
        {
            if (string.IsNullOrEmpty(value)) return "";
            return new string(value.Take(256).Select(c => char.IsControl(c) ? ' ' : c).ToArray()).Trim();
        }

        private void Notify(string message)
        {
            notice = message;
            noticeUntil = DateTime.UtcNow.AddSeconds(8);
        }

        private void LoadSettings()
        {
            try
            {
                if (!File.Exists(settingsFile)) return;
                string[] lines = File.ReadAllLines(settingsFile);
                if (lines.Length < 2) return;
                Source = Sources.FirstOrDefault(s => s == lines[0]) ?? "Local";
                // Keep entries from temporarily disconnected music drives.
                foreach (string path in lines.Skip(2))
                {
                    int saved;
                    if (path.StartsWith("volume=", StringComparison.Ordinal) && int.TryParse(path.Substring(7), out saved) && saved >= 0 && saved <= 100)
                        localVolume = saved;
                    if (IsAbsoluteFile(path) && !files.Contains(path, StringComparer.OrdinalIgnoreCase)) files.Add(path);
                }
                int index;
                TrackIndex = int.TryParse(lines[1], out index) && index >= 0 && index < files.Count ? index :
                    (files.Count > 0 ? 0 : -1);
            }
            catch (Exception ex) { Notify("Could not read the music library. " + DisplayText(ex.Message)); }
        }

        private void SaveSettings()
        {
            string temp = settingsFile + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(settingsFile));
                File.WriteAllLines(temp, new[] { Source, TrackIndex.ToString(CultureInfo.InvariantCulture),
                    "volume=" + localVolume.ToString(CultureInfo.InvariantCulture) }.Concat(files));
                try { File.Move(temp, settingsFile); }
                catch (IOException) when (File.Exists(settingsFile)) { File.Replace(temp, settingsFile, null); }
            }
            catch (Exception ex) { Notify("Could not save the music library. " + DisplayText(ex.Message)); }
            finally
            {
                try { File.Delete(temp); }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
            }
        }

        private static bool IsAbsoluteFile(string path)
        {
            Uri uri;
            return !string.IsNullOrWhiteSpace(path) && Uri.TryCreate(path, UriKind.Absolute, out uri) && uri.IsFile;
        }

        private void UpdateTracks()
        {
            var names = files.Select(Path.GetFileName).ToList();
            var duplicates = new HashSet<string>(names.GroupBy(n => n, StringComparer.OrdinalIgnoreCase)
                .Where(g => g.Count() > 1).Select(g => g.Key), StringComparer.OrdinalIgnoreCase);
            Tracks = files.Select((p, i) => duplicates.Contains(names[i]) ? names[i] + " (" + Path.GetDirectoryName(p) + ")" : names[i]).ToArray();
            var paths = files.Where(p => !tags.ContainsKey(p)).ToArray();
            var previous = indexing;
            indexing = Task.Run(async () =>
            {
                await previous.ConfigureAwait(false);
                foreach (var path in paths)
                {
                    if (tags.ContainsKey(path)) continue;
                    try
                    {
                        var file = await Windows.Storage.StorageFile.GetFileFromPathAsync(path);
                        var info = await file.Properties.GetMusicPropertiesAsync();
                        tags[path] = new[] {info.Title, info.Artist, info.AlbumArtist, info.Album};
                    }
                    catch (Exception) { /* Offline files can still be found by their filename. */ }
                }
            });
        }

        public void AddFiles(string[] paths)
        {
            int before = files.Count;
            foreach (string path in paths ?? new string[0])
            {
                if (!IsAbsoluteFile(path) || !File.Exists(path)) continue;
                string full = Path.GetFullPath(path);
                if (!files.Contains(full, StringComparer.OrdinalIgnoreCase)) files.Add(full);
            }
            if (TrackIndex < 0 && files.Count > 0) TrackIndex = 0;
            if (before != files.Count)
            {
                UpdateTracks();
                if (Source == "Local") UpdateLocal();
                Notify((files.Count - before).ToString(CultureInfo.InvariantCulture) + " track(s) added.");
                SaveSettings();
            }
            else Notify("No new local files to add.");
        }

        public async Task RefreshAsync()
        {
            // Host and window polls may overlap while an explicit command awaits the provider.
            if (!operations.Wait(0)) return;
            try { await RefreshCoreAsync(); }
            finally { operations.Release(); }
        }

        private Task RefreshCoreAsync()
        {
            if (Source != "Local") return UpdateRemoteAsync();
            UpdateLocal();
            return Task.CompletedTask;
        }

        public async Task CommandAsync(string action, string argument, string expectedSource = null)
        {
            action = (action ?? "").Trim().ToLowerInvariant();
            argument = (argument ?? "").Trim();
            int index;
            Session requested = action == "session" && int.TryParse(argument, out index) && index >= 0 && index < available.Count
                ? available[index] : null;
            await operations.WaitAsync();
            try
            {
                noticeUntil = DateTime.MinValue;
                ChooseSearchResult = false;
                if (!string.IsNullOrEmpty(expectedSource) && expectedSource != Source)
                {
                    Notify("Music source changed. Try the command again.");
                    return;
                }
                switch (action)
                {
                    case "refresh": break;
                    case "source":
                        string source = Sources.FirstOrDefault(s => s.Equals(argument, StringComparison.OrdinalIgnoreCase));
                        if (source == null) { Notify("Unknown music source."); break; }
                        if (Source == source) break;
                        if (Source == "Local") PauseLocal();
                        Source = source;
                        selected = null;
                        explicitSelection = false;
                        available.Clear();
                        captions.Clear();
                        captionRefresh = DateTime.MinValue;
                        Sessions = new string[0];
                        ClearRemote();
                        SaveSettings();
                        break;
                    case "session":
                        if (Source == "Local" || requested == null || !available.Contains(requested))
                        { Notify("Choose an available Windows media session."); break; }
                        selected = requested;
                        explicitSelection = true;
                        captionRefresh = DateTime.MinValue;
                        break;
                    case "open":
                        if (Source == "Local")
                        {
                            var picker = new OpenFileDialog { Title = "Add local music", Multiselect = true,
                                Filter = "Music files|*.mp3;*.m4a;*.aac;*.wav;*.flac;*.wma;*.ogg;*.aiff;*.aif|All files|*.*" };
                            if (picker.ShowDialog() == true) AddFiles(picker.FileNames);
                        }
                        else OpenProvider(null);
                        break;
                    case "search":
                    case "playquery":
                        if (argument.Length == 0) { Notify("Enter a track name to search."); break; }
                        if (Source == "Local") await FindLocal(argument);
                        else OpenProvider(argument);
                        break;
                    case "volume": await SetVolume(argument); break;
                    default:
                        if (Source == "Local") LocalCommand(action, argument);
                        else await RemoteCommandAsync(action, argument);
                        break;
                }
                await RefreshCoreAsync();
            }
            catch (Exception ex) { Notify("Music control failed. " + DisplayText(ex.GetBaseException().Message)); }
            finally { operations.Release(); }
        }

        private void OpenProvider(string query)
        {
            string encoded = query == null ? null : Uri.EscapeDataString(query);
            string url;
            switch (Source)
            {
                case "Spotify": url = "https://open.spotify.com/" + (encoded == null ? "" : "search/" + encoded); break;
                case "Apple Music": url = "https://music.apple.com/" + (encoded == null ? "" : "search?term=" + encoded); break;
                case "YouTube Music": url = "https://music.youtube.com/" + (encoded == null ? "" : "search?q=" + encoded); break;
                default: return;
            }
            using (Process.Start(new ProcessStartInfo(url) { UseShellExecute = true })) { }
            Notify(encoded == null ? Source + " opened. Start a song in the player." :
                Source + " search opened. Choose a result to play.");
        }

        internal bool MatchesLocal(int index, string query)
        {
            string[] fields;
            return Tracks[index].IndexOf(query, StringComparison.OrdinalIgnoreCase) >= 0 ||
                (tags.TryGetValue(files[index],out fields) && fields.Any(s => !string.IsNullOrEmpty(s) &&
                    s.IndexOf(query,StringComparison.OrdinalIgnoreCase) >= 0));
        }

        private async Task FindLocal(string query)
        {
            var names = files.Select(Path.GetFileNameWithoutExtension).ToArray();
            var matches = Enumerable.Range(0, names.Length).Where(i =>
                query.Equals(names[i], StringComparison.OrdinalIgnoreCase) ||
                query.Equals(Path.GetFileName(files[i]), StringComparison.OrdinalIgnoreCase) ||
                query.Equals(Tracks[i], StringComparison.OrdinalIgnoreCase)).ToList();
            if (matches.Count == 0)
            {
                if (!indexing.IsCompleted) await Task.WhenAny(indexing, Task.Delay(1200));
                matches = Enumerable.Range(0, names.Length).Where(i => MatchesLocal(i,query)).ToList();
                if (!indexing.IsCompleted) { ChooseSearchResult = true; Notify("Searching the local library in the desktop player."); return; }
            }
            ChooseSearchResult = matches.Count > 1;
            if (matches.Count == 1) StartLocal(matches[0]);
            else Notify(matches.Count == 0 ? "No local track matches that name." :
                "Several tracks match. Choose one in the desktop library.");
        }

        private void LocalCommand(string action, string argument)
        {
            int index;
            switch (action)
            {
                case "track":
                    if (int.TryParse(argument, out index) && index >= 0 && index < files.Count) StartLocal(index);
                    else Notify("Choose a track in the local library.");
                    break;
                case "toggle":
                    if (localWantsPlay) PauseLocal();
                    else PlayLocal();
                    break;
                case "play": PlayLocal(); break;
                case "pause": PauseLocal(); break;
                case "next":
                    if (TrackIndex + 1 < files.Count) StartLocal(TrackIndex + 1);
                    else Notify("At the end of the local library.");
                    break;
                case "previous":
                    if (TrackIndex > 0) StartLocal(TrackIndex - 1);
                    else Notify("At the start of the local library.");
                    break;
                case "seek":
                    double target;
                    if (CanSeek && ParseSeconds(argument, out target))
                        player.Position = TimeSpan.FromSeconds(Math.Min(Duration, target));
                    else Notify("Seeking is unavailable.");
                    break;
                default: Notify("Unknown music control."); break;
            }
        }

        private void PlayLocal()
        {
            if (TrackIndex < 0) { Notify("Add music files to the desktop library."); return; }
            if (player == null || localError != null) { StartLocal(TrackIndex); return; }
            localWantsPlay = true;
            if (localOpened) player.Play();
        }

        private void PauseLocal()
        {
            localWantsPlay = false;
            if (player != null && localOpened) player.Pause();
        }

        private void StartLocal(int index)
        {
            var previous = player;
            player = null;
            if (previous != null) previous.Close();
            bool selectionChanged = TrackIndex != index;
            TrackIndex = index;
            localOpened = false;
            localWantsPlay = false;
            localError = null;
            if (selectionChanged) SaveSettings();
            if (!File.Exists(files[index]))
            {
                localError = "File unavailable. Reconnect its drive or choose another track.";
                UpdateLocal();
                return;
            }
            var current = new MediaPlayer { Volume = localVolume / 100.0 };
            player = current;
            localWantsPlay = true;
            current.MediaOpened += (sender, args) =>
            {
                if (player != current) return;
                localOpened = true;
                if (localWantsPlay && Source == "Local") current.Play();
                if (Source == "Local") UpdateLocal();
            };
            current.MediaFailed += (sender, args) =>
            {
                if (player != current) return;
                localOpened = false;
                localWantsPlay = false;
                localError = "Unable to play this file. " + DisplayText(args.ErrorException.Message);
                if (Source == "Local") UpdateLocal();
            };
            current.MediaEnded += (sender, args) =>
            {
                if (player != current || !localWantsPlay || Source != "Local") return;
                if (TrackIndex + 1 < files.Count) StartLocal(TrackIndex + 1);
                else { PauseLocal(); current.Position = TimeSpan.Zero; }
                UpdateLocal();
            };
            current.Open(new Uri(files[index], UriKind.Absolute));
            UpdateLocal();
        }

        private void UpdateLocal()
        {
            Volume = localVolume;
            Artwork.Local(TrackIndex >= 0 ? files[TrackIndex] : null);
            Title = TrackIndex >= 0 ? DisplayText(Path.GetFileNameWithoutExtension(files[TrackIndex])) : "";
            Artist = "";
            string[] trackTags;
            if (TrackIndex >= 0 && tags.TryGetValue(files[TrackIndex],out trackTags))
            {
                if (!string.IsNullOrWhiteSpace(trackTags[0])) Title = DisplayText(trackTags[0]);
                Artist = DisplayText(trackTags[1]);
            }
            Playing = localOpened && localWantsPlay;
            Position = localOpened ? player.Position.TotalSeconds : 0;
            Duration = localOpened && player.NaturalDuration.HasTimeSpan ? player.NaturalDuration.TimeSpan.TotalSeconds : 0;
            CanSeek = Duration > 0;
            CanToggle = TrackIndex >= 0;
            CanNext = TrackIndex + 1 < files.Count;
            CanPrevious = TrackIndex > 0;
            state = localError ?? (TrackIndex < 0 ? "Add music files to the desktop library." :
                (Playing ? "Playing" : localWantsPlay ? "Opening track…" : localOpened ? "Paused" : "Ready"));
        }

        private void ClearRemote()
        {
            Volume = -1;
            volumeSession = null;
            Artwork.Clear();
            Title = Artist = "";
            Playing = CanToggle = CanNext = CanPrevious = CanSeek = false;
            Position = Duration = 0;
            state = available.Count == 0 ? "Start a song in " + Source + " to connect." :
                "Choose the matching Windows media session in the desktop player.";
        }

        // A browser session does not provide its tab URL. Bind generic sessions only by a user's
        // explicit choice and never restore a browser binding by app ID after the session disappears.
        private bool IsDedicated(string appId)
        {
            if (Source == "Spotify")
                return EqualsId(appId, "Spotify.exe", "Spotify", "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify");
            if (Source == "Apple Music")
                return EqualsId(appId, "AppleMusic.exe", "AppleInc.AppleMusicWin_nzyj5cx40ttqa!App",
                    "AppleInc.AppleMusicWin_nzyj5cx40ttqa!AppleMusic");
            return false;
        }

        private static bool EqualsId(string actual, params string[] choices)
        {
            return choices.Contains(actual, StringComparer.OrdinalIgnoreCase);
        }

        private static async Task<T> WithTimeout<T>(Task<T> task)
        {
            using (var timer = new CancellationTokenSource())
            {
                if (await Task.WhenAny(task, Task.Delay(TimeSpan.FromSeconds(3), timer.Token)) != task)
                {
                    // A delayed provider may finish after the UI already reported the timeout.
                    ObserveFault(task);
                    throw new TimeoutException("The media provider took too long to respond.");
                }
                timer.Cancel();
                return await task;
            }
        }

        private static async void ObserveFault(Task task)
        {
            try { await task; }
            catch (Exception) { /* The caller already reported the timeout. */ }
        }

        private async Task UpdateRemoteAsync()
        {
            if (DateTime.UtcNow < retryAfter) { ClearRemote(); state = remoteError; return; }
            try
            {
                if (manager == null) manager = await WithTimeout(GlobalSystemMediaTransportControlsSessionManager.RequestAsync().AsTask());
                var current = manager.GetSessions().ToList();
                available = available.Where(current.Contains).Concat(current.Where(s => !available.Contains(s))).ToList();
                foreach (var removed in captions.Keys.Where(s => !available.Contains(s)).ToList()) captions.Remove(removed);
                if (!available.Contains(selected))
                {
                    selected = null;
                    if (!explicitSelection)
                    {
                        var matches = available.Where(s => IsDedicated(s.SourceAppUserModelId)).Take(2).ToList();
                        if (matches.Count == 1) selected = matches[0];
                    }
                }
                // Only refresh unselected captions occasionally. A slow unrelated app should
                // never delay transport or refresh for the selected session.
                if (DateTime.UtcNow >= captionRefresh || available.Any(s => !captions.ContainsKey(s)))
                {
                    captionRefresh = DateTime.UtcNow.AddSeconds(6);
                    foreach (var session in available.Where(s => s != selected))
                    {
                        if (!captions.ContainsKey(session)) captions[session] = "";
                        UpdateCaptionAsync(session);
                    }
                }
                if (selected == null) ClearRemote();
                else
                {
                    try { await ReadSelectedAsync(); }
                    catch (Exception ex)
                    {
                        ClearRemote();
                        state = "Cannot read this media session. " + DisplayText(ex.GetBaseException().Message);
                    }
                }
                UpdateSessionLabels();
            }
            catch (Exception ex)
            {
                manager = null;
                selected = null;
                available.Clear();
                captions.Clear();
                Sessions = new string[0];
                ClearRemote();
                remoteError = state = "Windows media controls unavailable. " + DisplayText(ex.GetBaseException().Message);
                retryAfter = DateTime.UtcNow.AddSeconds(4);
            }
        }

        private async void UpdateCaptionAsync(Session session)
        {
            try
            {
                var media = await WithTimeout(session.TryGetMediaPropertiesAsync().AsTask());
                if (!available.Contains(session) || session == selected) return;
                captions[session] = media == null ? "" : DisplayText(media.Title);
                UpdateSessionLabels();
            }
            catch (Exception) { /* Sessions may close between enumeration and reading a title. */ }
        }

        private void UpdateSessionLabels()
        {
            Sessions = available.Select(s =>
            {
                string title;
                string name = DisplayText(s.SourceAppUserModelId);
                return captions.TryGetValue(s, out title) && title.Length > 0 ? name + " · " + title : name;
            }).ToArray();
        }

        private async Task ReadSelectedAsync()
        {
            var media = await WithTimeout(selected.TryGetMediaPropertiesAsync().AsTask());
            var info = selected.GetPlaybackInfo();
            var timeline = selected.GetTimelineProperties();
            Title = media == null ? "" : DisplayText(media.Title);
            Artist = media == null ? "" : DisplayText(media.Artist);
            Artwork.Remote(selected, media);
            captions[selected] = Title;
            if (selected != volumeSession || DateTime.UtcNow >= volumeRefresh)
            {
                string appId = selected.SourceAppUserModelId;
                Volume = await Task.Run(() => AppVolume.ReadOrSet(appId));
                volumeSession = selected;
                volumeRefresh = DateTime.UtcNow.AddSeconds(2);
            }
            if (info == null || info.Controls == null)
            {
                Playing = CanToggle = CanNext = CanPrevious = CanSeek = false;
                Position = Duration = 0;
                state = "Waiting for playback controls from this session.";
                return;
            }
            var controls = info.Controls;
            Playing = info.PlaybackStatus == PlaybackStatus.Playing;
            CanToggle = controls.IsPlayPauseToggleEnabled || (Playing ? controls.IsPauseEnabled : controls.IsPlayEnabled);
            CanPrevious = controls.IsPreviousEnabled;
            CanNext = controls.IsNextEnabled;
            Duration = timeline == null ? 0 : Math.Max(0, (timeline.EndTime - timeline.StartTime).TotalSeconds);
            Position = timeline == null ? 0 : (timeline.Position - timeline.StartTime).TotalSeconds;
            if (Duration > 0 && Playing && timeline.LastUpdatedTime > DateTimeOffset.FromUnixTimeSeconds(0))
                Position += Math.Max(0, (DateTimeOffset.UtcNow - timeline.LastUpdatedTime).TotalSeconds) * (info.PlaybackRate ?? 1.0);
            Position = Duration > 0 ? Math.Max(0, Math.Min(Duration, Position)) : 0;
            CanSeek = controls.IsPlaybackPositionEnabled && Duration > 0;
            state = info.PlaybackStatus.ToString() + (explicitSelection ? " in " + Source : "");
        }

        private static bool ParseSeconds(string value, out double seconds)
        {
            return double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out seconds) &&
                !double.IsNaN(seconds) && !double.IsInfinity(seconds) && seconds >= 0;
        }

        private async Task SetVolume(string argument)
        {
            int value;
            if (!int.TryParse(argument, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out value) ||
                value < -100 || value > 100)
            { Notify("Use musicvolume 0 to 100, or a change such as +5 or -5."); return; }
            bool relative = argument.StartsWith("+") || argument.StartsWith("-");
            if (Source == "Local")
            {
                localVolume = AppVolume.Adjust(localVolume, value, relative);
                if (player != null) player.Volume = localVolume / 100.0;
                SaveSettings();
            }
            else if (selected != null && manager != null && manager.GetSessions().Contains(selected))
            {
                string appId = selected.SourceAppUserModelId;
                Volume = await Task.Run(() => AppVolume.ReadOrSet(appId, value, relative));
                volumeRefresh = DateTime.UtcNow.AddSeconds(2);
                if (Volume < 0) Notify("No matching app volume is available on this PC.");
            }
            else Notify("Choose an active playback session to adjust its volume.");
        }

        private async Task RemoteCommandAsync(string action, string argument)
        {
            // Use the specific session backing the visible controls. The system-wide current session
            // may belong to another app and must never be used as a transport fallback.
            Session session = selected;
            if (session == null || manager == null || !manager.GetSessions().Contains(session))
            { Notify("Choose an active " + Source + " session in the desktop player."); return; }
            var info = session.GetPlaybackInfo();
            if (info == null || info.Controls == null) { Notify("This session has no playback controls."); return; }
            var controls = info.Controls;
            bool playing = info.PlaybackStatus == PlaybackStatus.Playing;
            Task<bool> result = null;
            switch (action)
            {
                case "toggle":
                case "play":
                case "pause":
                    bool wantPlay = action == "play" || (action == "toggle" && !playing);
                    if (wantPlay == playing) return;
                    if (wantPlay && controls.IsPlayEnabled) result = session.TryPlayAsync().AsTask();
                    else if (!wantPlay && controls.IsPauseEnabled) result = session.TryPauseAsync().AsTask();
                    else if (controls.IsPlayPauseToggleEnabled) result = session.TryTogglePlayPauseAsync().AsTask();
                    break;
                case "next":
                    if (controls.IsNextEnabled) result = session.TrySkipNextAsync().AsTask();
                    break;
                case "previous":
                    if (controls.IsPreviousEnabled) result = session.TrySkipPreviousAsync().AsTask();
                    break;
                case "seek":
                    double seconds;
                    if (controls.IsPlaybackPositionEnabled && ParseSeconds(argument, out seconds))
                    {
                        var timeline = session.GetTimelineProperties();
                        if (timeline == null) break;
                        double length = (timeline.EndTime - timeline.StartTime).TotalSeconds;
                        if (length <= 0) break;
                        TimeSpan target = timeline.StartTime + TimeSpan.FromSeconds(Math.Min(length, seconds));
                        if (timeline.MaxSeekTime > timeline.MinSeekTime)
                            target = TimeSpan.FromTicks(Math.Max(timeline.MinSeekTime.Ticks, Math.Min(timeline.MaxSeekTime.Ticks, target.Ticks)));
                        result = session.TryChangePlaybackPositionAsync(target.Ticks).AsTask();
                    }
                    break;
                default: Notify("Unknown music control."); return;
            }
            if (result == null) Notify("This session does not support that control.");
            else if (!await WithTimeout(result)) Notify("The media provider declined that control.");
        }
    }
}
