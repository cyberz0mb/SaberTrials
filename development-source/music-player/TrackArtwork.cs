using System;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Windows.Graphics.Imaging;
using Windows.Storage;
using Windows.Storage.FileProperties;
using Windows.Storage.Streams;
using Windows.Media.Control;
using Session = Windows.Media.Control.GlobalSystemMediaTransportControlsSession;
using BitmapDecoder = Windows.Graphics.Imaging.BitmapDecoder;

namespace SaberTrials.Music
{
    // The desktop displays a frozen WPF image. The game reads the same bounded
    // RGBA pixels once per cover through a session-local, read-only view.
    internal sealed class TrackArtwork
    {
        internal const int Size = 256;
        private readonly Dispatcher owner = Dispatcher.CurrentDispatcher;
        private Session session;
        private string track;
        private bool hadThumbnail;
        private int metadataChanged;
        private CancellationTokenSource loading;
        private byte[] pixels;
        private MemoryMappedFile shared;
        private string token;
        private DateTime retryAfter;
        internal BitmapSource Image { get; private set; }

        internal string GameToken()
        {
            if (pixels == null) return "-";
            if (shared != null) return token;
            string id = Guid.NewGuid().ToString("N");
            MemoryMappedFile mapping = null;
            try
            {
                mapping = MemoryMappedFile.CreateNew(@"Local\SaberTrials.Music.Cover." + id, pixels.Length);
                using (var view = mapping.CreateViewAccessor(0, pixels.Length, MemoryMappedFileAccess.Write))
                    view.WriteArray(0, pixels, 0, pixels.Length);
                shared = mapping;
                token = id;
                return id;
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
            {
                mapping?.Dispose();
                return "-";
            }
        }

        private void SetPixels(byte[] next)
        {
            if (ReferenceEquals(pixels, next) || (pixels != null && next != null && pixels.SequenceEqual(next))) return;
            shared?.Dispose();
            shared = null;
            pixels = next;
            Image = null;
            if (next == null) return;
            byte[] bgra = (byte[])next.Clone();
            for (int i = 0; i < bgra.Length; i += 4)
            {
                bgra[i] = next[i + 2];
                bgra[i + 2] = next[i];
            }
            Image = BitmapSource.Create(Size, Size, 96, 96, PixelFormats.Bgra32, null, bgra, Size * 4);
            Image.Freeze();
        }

        internal void Clear()
        {
            if (session != null) session.MediaPropertiesChanged -= MetadataChanged;
            session = null;
            track = null;
            hadThumbnail = false;
            Interlocked.Exchange(ref metadataChanged, 0);
            loading?.Cancel();
            loading = null;
            retryAfter = DateTime.MinValue;
            SetPixels(null);
        }

        private void MetadataChanged(Session sender, MediaPropertiesChangedEventArgs args)
        {
            Interlocked.Exchange(ref metadataChanged, 1);
        }

        internal void Local(string path)
        {
            if (session == null && track == path) return;
            Clear();
            if (path == null) return;
            track = path;
            StartRead(async ct =>
            {
                var file = await StorageFile.GetFileFromPathAsync(path).AsTask(ct).ConfigureAwait(false);
                using (var thumb = await file.GetThumbnailAsync(ThumbnailMode.MusicView, Size,
                    ThumbnailOptions.ResizeThumbnail).AsTask(ct).ConfigureAwait(false))
                {
                    return thumb != null && thumb.Type == ThumbnailType.Image ? await Decode(thumb, ct).ConfigureAwait(false) : null;
                }
            });
        }

        internal void Remote(Session current, GlobalSystemMediaTransportControlsSessionMediaProperties media)
        {
            if (media == null) { Clear(); return; }
            string key = string.Join("\t", media.Title, media.Artist, media.AlbumTitle, media.TrackNumber.ToString());
            bool changed = session != current || track != key;
            if (changed)
            {
                Clear();
                session = current;
                session.MediaPropertiesChanged += MetadataChanged;
                track = key;
            }
            var thumbnail = media.Thumbnail;
            bool dirty = Interlocked.Exchange(ref metadataChanged, 0) != 0;
            if (thumbnail == null)
            {
                if (hadThumbnail) { loading?.Cancel(); loading = null; SetPixels(null); }
                hadThumbnail = false;
                return;
            }
            if (!changed && hadThumbnail && !dirty &&
                (pixels != null || loading != null || DateTime.UtcNow < retryAfter)) return;
            hadThumbnail = true;
            StartRead(async ct =>
            {
                using (var stream = await thumbnail.OpenReadAsync().AsTask(ct).ConfigureAwait(false))
                    return await Decode(stream, ct).ConfigureAwait(false);
            });
        }

        private void StartRead(Func<CancellationToken, Task<byte[]>> read)
        {
            loading?.Cancel();
            var request = new CancellationTokenSource(TimeSpan.FromSeconds(8));
            loading = request;
            _ = ReadAsync(read, request);
        }

        private async Task ReadAsync(Func<CancellationToken, Task<byte[]>> read, CancellationTokenSource request)
        {
            byte[] result = null;
            try { result = await Task.Run(() => read(request.Token)).ConfigureAwait(false); }
            catch (Exception) { /* Missing, expired and undecodable artwork all use the record. */ }
            await owner.InvokeAsync(() =>
            {
                if (request == loading)
                {
                    loading = null;
                    retryAfter = DateTime.UtcNow.AddSeconds(20);
                    SetPixels(result);
                }
                request.Dispose();
            });
        }

        private static async Task<byte[]> Decode(IRandomAccessStream stream, CancellationToken ct)
        {
            if (stream == null || stream.Size == 0 || stream.Size > 16 * 1024 * 1024) return null;
            var decoder = await BitmapDecoder.CreateAsync(stream).AsTask(ct).ConfigureAwait(false);
            uint w = decoder.PixelWidth, h = decoder.PixelHeight;
            if (w == 0 || h == 0 || (ulong)w * h > 32000000) return null;
            double scale = (double)Size / Math.Max(w, h);
            int width = Math.Max(1, (int)Math.Round(w * scale)), height = Math.Max(1, (int)Math.Round(h * scale));
            var transform = new BitmapTransform { ScaledWidth = (uint)width, ScaledHeight = (uint)height,
                InterpolationMode = BitmapInterpolationMode.Fant };
            var provider = await decoder.GetPixelDataAsync(BitmapPixelFormat.Rgba8, BitmapAlphaMode.Straight, transform,
                ExifOrientationMode.IgnoreExifOrientation, ColorManagementMode.ColorManageToSRgb).AsTask(ct).ConfigureAwait(false);
            var src = provider.DetachPixelData();
            if (src.Length != width * height * 4) return null;
            if (width == Size && height == Size) return src;
            var image = new byte[Size * Size * 4];
            int offset = ((Size - height) / 2 * Size + (Size - width) / 2) * 4;
            for (int row = 0; row < height; row++)
                System.Buffer.BlockCopy(src, row * width * 4, image, offset + row * Size * 4, width * 4);
            return image;
        }
    }
}
