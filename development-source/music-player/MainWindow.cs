using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;

namespace SaberTrials.Music
{
    public sealed class MainWindow : Window
    {
        private static readonly string[] Sources = { "Local", "Spotify", "Apple Music", "YouTube Music" };
        private static readonly Geometry PlayIcon = Geometry.Parse("M2,1 L15,9 L2,17 Z");
        private static readonly Geometry PauseIcon = Geometry.Parse("M1,1 H6 V17 H1 Z M10,1 H15 V17 H10 Z");
        private readonly MusicModel model;
        private readonly Grid layout;
        private readonly RadioButton[] tabs = new RadioButton[Sources.Length];
        private readonly Dictionary<string, string> queries = new Dictionary<string, string>();
        private string[] library = new string[0];
        private string[] sessions = new string[0];
        private string shownSource;
        private int activeTrack = -1;
        private int indexedTracks;
        private bool adjustingVolume;
        private bool savingVolume;
        internal void FilterLibrary(string query) { El<TextBox>("Search").Text = query; }
        private bool syncing;
        private bool busy;
        private bool draggingSeek;
        private string error;
        private DateTime errorUntil;

        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr window, int attr, ref int value, int length);

        public MainWindow(MusicModel model)
        {
            this.model = model ?? throw new ArgumentNullException(nameof(model));
            Title = "Saber Trials Music Player";
            Background = new SolidColorBrush(Color.FromRgb(11, 17, 25));
            WindowStartupLocation = WindowStartupLocation.CenterScreen;
            MinWidth = 435;
            MinHeight = 380;
            Width = Math.Min(876, Math.Max(MinWidth, SystemParameters.WorkArea.Width - 36));
            Height = Math.Min(680, Math.Max(MinHeight, SystemParameters.WorkArea.Height - 30));
            using (Stream stream = Resource("MainWindow.xaml"))
                layout = (Grid)XamlReader.Load(stream);
            Content = layout;

            var emblem = ImageResource("Emblem.png");
            El<Image>("BrandEmblem").Source = emblem;
            El<Image>("BrandWordmark").Source = ImageResource("Wordmark.png");
            El<Grid>("ArtHost").Children.Add(new RecordArtwork(emblem));
            MakeSourceTabs();

            El<Button>("Previous").Click += async (s, e) => await Send("previous");
            El<Button>("Next").Click += async (s, e) => await Send("next");
            El<Button>("Toggle").Click += async (s, e) => await Send("toggle");
            El<Button>("SourceAction").Click += async (s, e) => await Send("open");
            El<Button>("SubmitSearch").Click += async (s, e) => await SearchService();
            var query = El<TextBox>("Search");
            query.TextChanged += (s, e) =>
            {
                if (syncing) return;
                queries[shownSource] = query.Text;
                SetSearchState();
                if (shownSource == "Local") RenderTracks();
            };
            query.KeyDown += async (s, e) =>
            {
                if (e.Key != Key.Enter) return;
                e.Handled = true;
                if (shownSource != "Local") await SearchService();
                else if (!string.IsNullOrWhiteSpace(query.Text)) await Send("playquery", query.Text.Trim());
            };

            var tracks = El<ListBox>("Tracks");
            tracks.AddHandler(ButtonBase.ClickEvent, new RoutedEventHandler(async (s, e) =>
            {
                var button = e.OriginalSource as Button;
                if (button != null && button.Tag is int)
                {
                    e.Handled = true;
                    await PlayTrack((int)button.Tag);
                }
            }));
            tracks.MouseDoubleClick += async (s, e) =>
            {
                if (e.ChangedButton != MouseButton.Left || IsInsideButton(e.OriginalSource as DependencyObject)) return;
                var item = ItemsControl.ContainerFromElement(tracks, e.OriginalSource as DependencyObject) as ListBoxItem;
                var row = item == null ? null : item.DataContext as TrackRow;
                if (row != null) { e.Handled = true; await PlayTrack(row.Index); }
            };
            tracks.PreviewKeyDown += async (s, e) =>
            {
                var row = tracks.SelectedItem as TrackRow;
                if (row != null && e.Key == Key.Enter) { e.Handled = true; await PlayTrack(row.Index); }
            };
            El<ListBox>("Sessions").SelectionChanged += async (s, e) =>
            {
                var list = (ListBox)s;
                if (!syncing && list.SelectedIndex >= 0 && list.SelectedIndex != model.SessionIndex)
                    await Send("session", list.SelectedIndex.ToString(CultureInfo.InvariantCulture));
            };

            var volume = El<Slider>("Volume");
            volume.PreviewMouseLeftButtonDown += (s,e) =>
            {
                if (!volume.IsEnabled) return;
                volume.Focus();
                adjustingVolume = true;
                volume.CaptureMouse();
                volume.Value = PointerValue(volume, e.GetPosition(volume).X);
                e.Handled = true;
            };
            volume.PreviewMouseMove += (s,e) =>
            {
                if (adjustingVolume) volume.Value = PointerValue(volume, e.GetPosition(volume).X);
            };
            volume.PreviewMouseLeftButtonUp += async (s,e) =>
            {
                if (!adjustingVolume || e.ChangedButton != MouseButton.Left) return;
                volume.Value = PointerValue(volume, e.GetPosition(volume).X);
                adjustingVolume = false;
                volume.ReleaseMouseCapture();
                e.Handled = true;
                await Send("volume", Math.Round(volume.Value).ToString(CultureInfo.InvariantCulture));
            };
            volume.LostMouseCapture += (s,e) => adjustingVolume = false;
            volume.ValueChanged += async (s,e) =>
            {
                if (syncing) return;
                El<TextBlock>("VolumeValue").Text = Math.Round(volume.Value) + "%";
                if (!adjustingVolume)
                    await Send("volume", Math.Round(volume.Value).ToString(CultureInfo.InvariantCulture));
            };
            var seek = El<Slider>("Seek");
            seek.PreviewMouseLeftButtonDown += (s, e) =>
            {
                if (!seek.IsEnabled || model.Duration <= 0) return;
                seek.Focus();
                draggingSeek = true;
                seek.CaptureMouse();
                UpdateSeekPreview(e.GetPosition(seek).X);
                e.Handled = true;
            };
            seek.PreviewMouseMove += (s, e) =>
            {
                if (draggingSeek) UpdateSeekPreview(e.GetPosition(seek).X);
            };
            seek.PreviewMouseLeftButtonUp += async (s, e) =>
            {
                if (!draggingSeek) return;
                UpdateSeekPreview(e.GetPosition(seek).X);
                double value = seek.Value;
                EndDrag();
                e.Handled = true;
                await SeekTo(value);
            };
            seek.LostMouseCapture += (s, e) => draggingSeek = false;
            seek.PreviewKeyDown += async (s, e) =>
            {
                double value = seek.Value;
                switch (e.Key)
                {
                    case Key.Home: value = 0; break;
                    case Key.End: value = model.Duration; break;
                    case Key.Left: case Key.Down: value -= 5; break;
                    case Key.Right: case Key.Up: value += 5; break;
                    case Key.PageDown: value -= 15; break;
                    case Key.PageUp: value += 15; break;
                    default: return;
                }
                e.Handled = true;
                await SeekTo(value);
            };

            layout.SizeChanged += (s, e) => ApplySize(e.NewSize.Width);
            SourceInitialized += (s, e) =>
            {
                // The standard system caption retains Windows snap, resize, keyboard and taskbar behavior.
                int enabled = 1;
                IntPtr handle = new WindowInteropHelper(this).Handle;
                if (DwmSetWindowAttribute(handle, 20, ref enabled, sizeof(int)) != 0)
                    DwmSetWindowAttribute(handle, 19, ref enabled, sizeof(int));
            };
            ApplySize(Width);
            Sync();
        }

        private static Stream Resource(string name)
        {
            string id = "SaberTrials.Music." + name;
            return typeof(MainWindow).Assembly.GetManifestResourceStream(id)
                ?? throw new InvalidDataException("Missing player resource " + id);
        }

        private static BitmapImage ImageResource(string name)
        {
            using (Stream stream = Resource(name))
            {
                var image = new BitmapImage();
                image.BeginInit();
                image.CacheOption = BitmapCacheOption.OnLoad;
                image.StreamSource = stream;
                image.EndInit();
                image.Freeze();
                return image;
            }
        }

        private T El<T>(string name) where T : class { return (T)layout.FindName(name); }
        private static Visibility Show(bool visible) { return visible ? Visibility.Visible : Visibility.Collapsed; }

        private static bool IsInsideButton(DependencyObject node)
        {
            while (node is Visual)
            {
                if (node is ButtonBase) return true;
                node = VisualTreeHelper.GetParent(node);
            }
            return false;
        }

        private void MakeSourceTabs()
        {
            var icons = new[]
            {
                "M1.5,5 Q1.5,4 2.5,4 H6.4 L8.6,6 H15 Q16,6 16,7 V13 Q16,14 15,14 H2.5 Q1.5,14 1.5,13 Z",
                "M1.5,5.7 Q8.5,2.3 16,6.2 M3,9 Q8.8,6.4 14.7,9.6 M4.4,12.2 Q9,10.4 13.3,12.8",
                "M6,12.5 V4.4 L14.2,2.5 V10.7 M6,6.7 L14.2,4.7 M6,12.4 C6,15 1,15.8 1,13 C1,10.9 6,10 6,12.4 M14.2,10.6 C14.2,13.2 9.2,14 9.2,11.3 C9.2,9.2 14.2,8.2 14.2,10.6",
                "M16,8 A7,7 0 1 1 2,8 A7,7 0 1 1 16,8 M7.5,5 L12,8 L7.5,11 Z"
            };
            var panel = El<UniformGrid>("SourceTabs");
            for (int i = 0; i < Sources.Length; ++i)
            {
                string source = Sources[i];
                string label = source == "Local" ? "Local files" : source;
                var tab = new RadioButton { Style = (Style)layout.Resources["SourceTab"], Tag = source };
                AutomationProperties.SetName(tab, label);
                var stack = new StackPanel { Orientation = Orientation.Horizontal };
                var icon = new System.Windows.Shapes.Path
                {
                    Data = Geometry.Parse(icons[i]), Width = 17, Height = 16, Stretch = Stretch.Uniform,
                    StrokeThickness = 1.65, StrokeLineJoin = PenLineJoin.Round,
                    StrokeStartLineCap = PenLineCap.Round, StrokeEndLineCap = PenLineCap.Round,
                    VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 7, 0)
                };
                icon.SetBinding(Shape.StrokeProperty, new System.Windows.Data.Binding("Foreground") { Source = tab });
                stack.Children.Add(icon);
                stack.Children.Add(new TextBlock { Text = label, VerticalAlignment = VerticalAlignment.Center });
                tab.Content = stack;
                tab.Click += async (s, e) =>
                {
                    if (!syncing && source != model.Source) await Send("source", source);
                };
                tabs[i] = tab;
                panel.Children.Add(tab);
            }
        }

        private void ApplySize(double width)
        {
            bool small = width < 680;
            int margin = width < 550 ? 12 : small ? 18 : 26;
            El<StackPanel>("MainColumn").Margin = new Thickness(margin, small ? 10 : 15, margin, 16);
            El<Grid>("Hero").Height = small ? 211 : 235;
            El<ColumnDefinition>("ArtColumn").Width = new GridLength(width < 500 ? 0.31 : small ? 0.44 : 0.74, GridUnitType.Star);
            El<StackPanel>("HeroDetails").Margin = new Thickness(small ? 16 : 25, 10, 5, 10);
            El<TextBlock>("TrackTitle").FontSize = small ? 27 : 35;
            foreach (RadioButton tab in tabs)
            {
                if (tab == null) continue;
                ((StackPanel)tab.Content).Children[0].Visibility = Show(width >= 540);
                tab.FontSize = width < 500 ? 12 : 13;
            }
        }

        private async Task Send(string action, string argument = "")
        {
            if (busy) return;
            busy = true;
            savingVolume = action == "volume";
            error = null;
            try
            {
                Sync();
                await model.CommandAsync(action, argument);
            }
            catch (Exception ex)
            {
                error = ex.GetBaseException().Message;
                errorUntil = DateTime.UtcNow.AddSeconds(12);
            }
            finally
            {
                savingVolume = false;
                busy = false;
                Sync();
            }
        }

        private Task SearchService()
        {
            string text = El<TextBox>("Search").Text.Trim();
            return text.Length == 0 ? Task.CompletedTask : Send("search", text);
        }

        private Task PlayTrack(int index)
        {
            return Send("track", index.ToString(CultureInfo.InvariantCulture));
        }

        private void EndDrag()
        {
            draggingSeek = false;
            var seek = El<Slider>("Seek");
            if (seek.IsMouseCaptured) seek.ReleaseMouseCapture();
        }

        private static double PointerValue(Slider slider, double x)
        {
            return Math.Max(0, Math.Min(1, (x - 5) / Math.Max(1, slider.ActualWidth - 10))) * slider.Maximum;
        }

        private void UpdateSeekPreview(double x)
        {
            var seek = El<Slider>("Seek");
            seek.Value = PointerValue(seek, x);
            El<TextBlock>("Elapsed").Text = Clock(seek.Value);
        }

        private Task SeekTo(double seconds)
        {
            seconds = Math.Max(0, Math.Min(seconds, model.Duration));
            return Send("seek", seconds.ToString("0.###", CultureInfo.InvariantCulture));
        }

        private static string Clock(double seconds)
        {
            if (double.IsNaN(seconds) || double.IsInfinity(seconds) || seconds < 0) return "–:––";
            var time = TimeSpan.FromSeconds(Math.Min(seconds, 359999));
            return time.TotalHours >= 1 ? ((int)time.TotalHours).ToString(CultureInfo.InvariantCulture) + time.ToString(@"\:mm\:ss") : time.ToString(@"m\:ss");
        }

        public void Sync()
        {
            var cover = model.Artwork.Image;
            El<Image>("AlbumCover").Source = cover;
            El<Border>("CoverFrame").Visibility = Show(cover != null);
            El<Grid>("ArtHost").Visibility = Show(cover == null);
            syncing = true;
            try
            {
                string source = string.IsNullOrEmpty(model.Source) ? "Local" : model.Source;
                bool local = source == "Local";
                bool changedSource = shownSource != source;
                if (changedSource)
                {
                    EndDrag();
                    shownSource = source;
                    string query;
                    queries.TryGetValue(source, out query);
                    El<TextBox>("Search").Text = query ?? "";
                }
                for (int i = 0; i < tabs.Length; ++i)
                {
                    tabs[i].IsChecked = Sources[i] == source;
                    tabs[i].IsEnabled = !busy;
                }
                string title = model.Title;
                var titleBlock = El<TextBlock>("TrackTitle");
                titleBlock.Text = string.IsNullOrWhiteSpace(title) ? "Nothing playing" : title;
                titleBlock.ToolTip = titleBlock.Text;
                string artist = model.Artist;
                if (string.IsNullOrWhiteSpace(artist))
                    artist = local ? "Music from your computer" : source;
                var artistBlock = El<TextBlock>("TrackArtist");
                artistBlock.Text = artist;
                artistBlock.ToolTip = artist;
                var toggle = El<Button>("Toggle");
                toggle.IsEnabled = !busy && model.CanToggle;
                string toggleLabel = model.Playing ? "Pause" : "Play";
                toggle.ToolTip = toggleLabel;
                AutomationProperties.SetName(toggle, toggleLabel);
                El<System.Windows.Shapes.Path>("ToggleGlyph").Data = model.Playing ? PauseIcon : PlayIcon;
                El<Button>("Previous").IsEnabled = !busy && model.CanPrevious;
                El<Button>("Next").IsEnabled = !busy && model.CanNext;
                var volume = El<Slider>("Volume");
                volume.IsEnabled = (!busy || savingVolume) && model.Volume >= 0;
                El<TextBlock>("VolumeName").Text = model.VolumeLabel;
                if (!adjustingVolume && !savingVolume)
                {
                    volume.Value = Math.Max(0, model.Volume);
                    El<TextBlock>("VolumeValue").Text = model.Volume < 0 ? "—" : model.Volume + "%";
                }
                double duration = model.Duration;
                if (double.IsInfinity(duration) || double.IsNaN(duration) || duration < 0) duration = 0;
                var seek = El<Slider>("Seek");
                seek.IsEnabled = !busy && duration > 0 && model.CanSeek;
                seek.Maximum = duration > 0 ? duration : 1;
                if (!draggingSeek)
                {
                    double position = model.Position;
                    if (double.IsInfinity(position) || double.IsNaN(position) || position < 0) position = 0;
                    seek.Value = duration > 0 ? Math.Min(position, duration) : 0;
                    El<TextBlock>("Elapsed").Text = Clock(position);
                }
                El<TextBlock>("Total").Text = duration > 0 ? Clock(duration) : "–:––";

                El<TextBlock>("Section").Text = local ? "Local library" : "Find music";
                var action = El<Button>("SourceAction");
                action.IsEnabled = !busy;
                action.Content = local ? "+  Add files" : "Open " + source + "  ↗";
                El<Border>("Library").Visibility = Show(local);
                El<StackPanel>("Service").Visibility = Show(!local);
                El<TextBlock>("TrackCount").Visibility = Show(local);
                int count = model.Tracks.Count;
                El<TextBlock>("TrackCount").Text = count == 1 ? "1 track" : count.ToString(CultureInfo.InvariantCulture) + " tracks";
                El<TextBlock>("SearchHandoff").Text = "Search results open in " + source + ". Choose a result there to play it.";
                var sessionHelp = El<TextBlock>("SessionHelp");
                var sessionList = El<ListBox>("Sessions");
                if (changedSource || !sessions.SequenceEqual(model.Sessions))
                {
                    sessions = model.Sessions.ToArray();
                    sessionList.ItemsSource = sessions;
                }
                sessionList.SelectedIndex = model.SessionIndex >= 0 && model.SessionIndex < sessions.Length ? model.SessionIndex : -1;
                sessionList.Visibility = Show(sessions.Length > 0);
                var prompt = El<TextBlock>("SessionPrompt");
                prompt.Visibility = Show(sessions.Length > 0 && model.SessionIndex < 0);
                prompt.Text = "Choose the session playing " + source + ".";
                sessionList.IsEnabled = !busy;
                sessionHelp.Visibility = Show(sessions.Length == 0);
                sessionHelp.Text = "Play a track in " + source + " to make its " +
                    (source == "YouTube Music" ? "browser session" : "playback session") + " available.";
                El<Grid>("SearchRow").Visibility = Show(!local || count > 0);
                SetSearchState();
                if (changedSource || !library.SequenceEqual(model.Tracks) || activeTrack != model.TrackIndex || indexedTracks != model.IndexedTracks)
                {
                    indexedTracks = model.IndexedTracks;
                    library = model.Tracks.ToArray();
                    activeTrack = model.TrackIndex;
                    RenderTracks();
                }
                El<ListBox>("Tracks").IsEnabled = !busy;
                string status = error != null && DateTime.UtcNow < errorUntil ? error : model.Status;
                var statusBlock = El<TextBlock>("PlayerStatus");
                statusBlock.Text = string.IsNullOrWhiteSpace(status) ? "Ready" : status;
                statusBlock.ToolTip = statusBlock.Text;
            }
            finally { syncing = false; }
        }

        private void SetSearchState()
        {
            bool local = shownSource == "Local";
            var query = El<TextBox>("Search");
            var hint = El<TextBlock>("SearchHint");
            string label = local ? "Find a local track" : "Search " + shownSource;
            hint.Text = label;
            AutomationProperties.SetName(query, label);
            hint.Visibility = Show(query.Text.Length == 0);
            var submit = El<Button>("SubmitSearch");
            submit.Visibility = Show(!local);
            submit.IsEnabled = !busy && !string.IsNullOrWhiteSpace(query.Text);
            submit.ToolTip = "Open results in " + shownSource;
        }

        private void RenderTracks()
        {
            string filter = El<TextBox>("Search").Text.Trim();
            var list = El<ListBox>("Tracks");
            var previous = list.SelectedItem as TrackRow;
            var rows = library.Select((name, index) => new TrackRow(index, name, index == activeTrack))
                .Where(row => model.MatchesLocal(row.Index,filter)).ToList();
            list.ItemsSource = rows;
            list.SelectedItem = rows.FirstOrDefault(row => row.Index == (previous == null ? activeTrack : previous.Index));
            list.Visibility = Show(rows.Count > 0);
            El<StackPanel>("EmptyLibrary").Visibility = Show(rows.Count == 0);
            El<TextBlock>("EmptyTitle").Text = library.Length == 0 ? "No tracks in your library" : "No matching tracks";
            El<TextBlock>("EmptyHelp").Text = library.Length == 0 ? "MP3, M4A, WAV, FLAC and other audio files." : "Try another song title or clear the search.";
        }

        private sealed class TrackRow
        {
            public int Index { get; private set; }
            public string Number { get; private set; }
            public string Name { get; private set; }
            public string PlayLabel { get { return "Play " + Name; } }
            public TrackRow(int index, string name, bool current)
            {
                Index = index;
                Name = name ?? "";
                Number = current ? "♪" : (index + 1).ToString(CultureInfo.InvariantCulture);
            }
            public override string ToString() { return Name; }
        }
    }
}

// Vector turntable artwork scales with the window. Its label uses the project's original menu emblem.
namespace SaberTrials.Music
{
    internal sealed class RecordArtwork : FrameworkElement
    {
        private readonly DrawingGroup illustration;

        public RecordArtwork(ImageSource emblem)
        {
            illustration = DrawDeck(emblem);
            illustration.Freeze();
            IsHitTestVisible = false;
        }

        private static Color ColorOf(string hex) { return (Color)ColorConverter.ConvertFromString(hex); }
        private static SolidColorBrush Ink(string hex) { return new SolidColorBrush(ColorOf(hex)); }
        private static Pen Line(string color, double width)
        {
            return new Pen(Ink(color), width) { StartLineCap = PenLineCap.Round, EndLineCap = PenLineCap.Round, LineJoin = PenLineJoin.Round };
        }

        private static LinearGradientBrush Wash(Point start, Point end, params string[] stops)
        {
            var brush = new LinearGradientBrush { StartPoint = start, EndPoint = end };
            for (int i = 0; i < stops.Length; ++i)
                brush.GradientStops.Add(new GradientStop(ColorOf(stops[i]), (double)i / (stops.Length - 1)));
            return brush;
        }

        private static Point Polar(Point center, double radius, double degrees)
        {
            double radians = degrees * Math.PI / 180;
            return new Point(center.X + Math.Cos(radians) * radius, center.Y + Math.Sin(radians) * radius);
        }

        private static StreamGeometry Arc(Point center, double radius, double start, double sweep, bool filled)
        {
            var geometry = new StreamGeometry();
            using (var path = geometry.Open())
            {
                var edge = Polar(center, radius, start);
                path.BeginFigure(filled ? center : edge, filled, filled);
                if (filled) path.LineTo(edge, true, false);
                path.ArcTo(Polar(center, radius, start + sweep), new Size(radius, radius), 0,
                    sweep > 180, SweepDirection.Clockwise, true, false);
            }
            return geometry;
        }

        private static BitmapSource PressedVinyl()
        {
            const int size = 520;
            byte[] pixels = new byte[size * size * 4];
            // Reflections on cut grooves follow the angle around the center. The two blue
            // lobes and the softer brass reflection fall across all the record bands together.
            for (int y = 0; y < size; ++y)
            for (int x = 0; x < size; ++x)
            {
                double px = (2 * x + 1.0) / size - 1;
                double py = (2 * y + 1.0) / size - 1;
                double radius = Math.Sqrt(px * px + py * py);
                if (radius > 1) continue;
                double angle = Math.Atan2(py, px);
                double blue = Math.Pow(Math.Abs(Math.Cos(angle - 0.77)), 11);
                double brass = Math.Pow(Math.Max(0, Math.Cos(angle + 1.19)), 18);
                double cuts = 0.5 + 0.5 * Math.Sin(radius * 584 + 0.32 * Math.Sin(radius * 78));
                double groove = cuts * cuts * (5.0 + 15 * blue + 7 * brass);
                double track = Math.Pow(0.5 + 0.5 * Math.Cos(radius * 81.3), 25) * 7;
                double light = 4.5 * (1 - py) + 3 * (1 - px) + groove - track;
                int i = (y * size + x) * 4;
                pixels[i] = (byte)Math.Max(0, 23 + light + 43 * blue + 8 * brass);
                pixels[i + 1] = (byte)Math.Max(0, 16 + light + 38 * blue + 16 * brass);
                pixels[i + 2] = (byte)Math.Max(0, 9 + light + 25 * blue + 22 * brass);
                pixels[i + 3] = (byte)Math.Min(255, (1 - radius) * size * 255);
            }
            var texture = BitmapSource.Create(size, size, 96, 96, PixelFormats.Bgra32, null, pixels, size * 4);
            texture.Freeze();
            return texture;
        }

        private static DrawingGroup DrawDeck(ImageSource emblem)
        {
            var art = new DrawingGroup();
            var c = new Point(172, 142);
            using (var d = art.Open())
            {
                // A few ruled chassis details behind the platter.
                for (int i = 0; i < 7; i++)
                {
                    double x = -90 + 73 * i;
                    d.DrawLine(Line("#28506D79", 0.6), new Point(x, 0), new Point(x - 52, 235));
                }
                d.DrawLine(Line("#405E7980", 1), new Point(242, 18), new Point(405, 18));
                d.DrawLine(Line("#294C6571", 1), new Point(254, 22), new Point(405, 22));
                d.DrawEllipse(Ink("#66000910"), null, new Point(c.X + 4, c.Y + 7), 151, 151);
                var metal = Wash(new Point(0, 0), new Point(1, 0.85), "#07121C", "#5A8590", "#122732", "#39535C", "#08121A");
                d.DrawEllipse(metal, Line("#547C87", 0.9), c, 147, 147);
                d.DrawEllipse(Ink("#11212B"), Line("#08151F", 2), c, 144, 144);
                for (int i = 0; i < 144; i++)
                {
                    double angle = i * 2.5;
                    d.DrawLine(Line(i % 3 == 0 ? "#AF78949B" : "#784C626C", 1.1), Polar(c, 143, angle), Polar(c, 145, angle));
                }
                d.DrawGeometry(null, Line("#9EE9F3", 1.35), Arc(c, 146.2, 198, 66, false));
                d.DrawGeometry(null, Line("#F3C375", 1.5), Arc(c, 146.2, 292, 17, false));
                d.DrawEllipse(Ink("#0A151D"), Line("#09141E", 1.4), c, 140, 140);
                d.DrawImage(PressedVinyl(), new Rect(c.X - 139.3, c.Y - 139.3, 278.6, 278.6));
                d.DrawEllipse(null, Line("#6688ABB3", 0.65), c, 133.8, 133.8);
                d.DrawEllipse(null, Line("#889FBCC1", 0.75), c, 138.4, 138.4);
                d.DrawEllipse(Ink("#132833"), Line("#A3BCC0", 1), c, 44.4, 44.4);
                var label = Wash(new Point(0, 0), new Point(1, 0.95), "#24505B", "#102A36", "#11202E");
                d.DrawEllipse(label, Line("#64828A", 1), c, 41.9, 41.9);
                d.DrawGeometry(null, Line("#C4A16D", 1.15), Arc(c, 39.4, 26, 112, false));
                d.DrawGeometry(null, Line("#64C7D3", 1.15), Arc(c, 39.4, 196, 111, false));
                d.DrawImage(emblem, new Rect(c.X - 23, c.Y - 23, 46, 46));
                d.DrawEllipse(Ink("#CCE5DC"), Line("#394F56", 1.1), c, 2.8, 2.8);

                var pivot = new Point(308, 26);
                var arm = Geometry.Parse("M308,26 L304,53 L302,82 Q302,87 298,92 L270,125");
                d.PushTransform(new TranslateTransform(4, 4));
                d.DrawGeometry(null, Line("#95071219", 8), arm);
                d.Pop();
                d.DrawEllipse(Ink("#0B1820"), Line("#567580", 1.3), pivot, 22.4, 22.4);
                d.DrawEllipse(metal, Line("#182B36", 2), pivot, 16.9, 16.9);
                d.DrawEllipse(Ink("#172D38"), Line("#8BA2A4", 1), pivot, 12.3, 12.3);
                d.DrawGeometry(null, Line("#091622", 7), arm);
                d.DrawGeometry(null, Line("#89A6AB", 4.4), arm);
                d.DrawGeometry(null, Line("#DEF0E9", 1.2), arm);
                d.DrawEllipse(Ink("#94AAA9"), Line("#28404B", 1), pivot, 4.6, 4.6);
                d.DrawGeometry(Ink("#1F323C"), Line("#93A7A6", 1.1), Geometry.Parse("M270,115 L280,124 L264,143 L254,135 Z"));
                d.DrawGeometry(Ink("#D4AB6C"), null, Geometry.Parse("M258,130 L267,138 L263,142 L255,135 Z"));
                d.DrawLine(Line("#EED3A2", 1.1), new Point(258, 139), new Point(255, 143));
            }
            return art;
        }

        protected override void OnRender(DrawingContext dc)
        {
            base.OnRender(dc);
            if (ActualHeight <= 0 || ActualWidth <= 0) return;
            double scale = ActualHeight / 235.0;
            double offset = ActualWidth * (ActualWidth < 135 ? 0.83 : 0.53) - 172 * scale;
            dc.PushClip(new RectangleGeometry(new Rect(RenderSize)));
            dc.PushTransform(new MatrixTransform(scale, 0, 0, scale, offset, 0));
            dc.DrawDrawing(illustration);
            dc.Pop();
            dc.Pop();
        }
    }
}
