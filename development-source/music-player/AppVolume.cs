using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace SaberTrials.Music
{
    // GSMTC identifies the player, while the Windows mixer owns its output gain.
    // Only operate on a uniquely identified application session, never the endpoint.
    internal static class AppVolume
    {
        internal static int Adjust(int current, int value, bool relative)
        {
            return Math.Max(0, Math.Min(100, relative ? current + value : value));
        }

        internal static string Browser(string id)
        {
            if (id == null) return null;
            foreach (string name in new[] { "MSEdge", "Chrome", "Firefox", "Brave", "Opera" })
                if (id.Equals(name, StringComparison.OrdinalIgnoreCase) ||
                    id.StartsWith(name + ".", StringComparison.OrdinalIgnoreCase) ||
                    id.StartsWith(name + "-", StringComparison.OrdinalIgnoreCase))
                    return name.ToLowerInvariant();
            return null;
        }

        private static bool Matches(string id, uint pid, int userSession)
        {
            if (pid == 0) return false;
            try
            {
                using (var p = Process.GetProcessById((int)pid))
                {
                    if (p.SessionId != userSession) return false;
                    string exe = p.ProcessName;
                    string known = Browser(id);
                    if (id.StartsWith("SpotifyAB.SpotifyMusic_", StringComparison.OrdinalIgnoreCase) ||
                        id.Equals("Spotify", StringComparison.OrdinalIgnoreCase)) known = "Spotify";
                    if (id.StartsWith("AppleInc.AppleMusicWin_", StringComparison.OrdinalIgnoreCase)) known = "AppleMusic";
                    if (known != null && exe.Equals(known,StringComparison.OrdinalIgnoreCase)) return true;
                    if (id.Equals(exe + ".exe",StringComparison.OrdinalIgnoreCase)) return true;
                    uint length = 512;
                    var aumid = new StringBuilder((int)length);
                    return GetApplicationUserModelId(p.Handle, ref length, aumid) == 0 &&
                        id.Equals(aumid.ToString(), StringComparison.OrdinalIgnoreCase);
                }
            }
            catch (Exception ex) when (ex is ArgumentException || ex is InvalidOperationException ||
                                       ex is System.ComponentModel.Win32Exception) { return false; }
        }

        internal static int ReadOrSet(string id, int? value = null, bool relative = false)
        {
            if (string.IsNullOrWhiteSpace(id)) return -1;
            var matches = new List<SessionControl>();
            var active = new List<SessionControl>();
            try
            {
                int userSession;
                using (var self = Process.GetCurrentProcess()) userSession = self.SessionId;
                var enumerator = (DeviceEnumerator)new MMDevices();
                try
                {
                    DeviceCollection devices;
                    enumerator.Endpoints(0, 1, out devices); // active render endpoints
                    try
                    {
                        uint count;
                        devices.Count(out count);
                        for (uint i = 0; i < count; ++i)
                        {
                            AudioDevice device;
                            devices.Item(i, out device);
                            try { Collect(device, id, userSession, matches, active); }
                            finally { Marshal.ReleaseComObject(device); }
                        }
                    }
                    finally { Marshal.ReleaseComObject(devices); }
                }
                finally { Marshal.ReleaseComObject(enumerator); }
                var candidates = active.Count > 0 ? active : matches;
                if (candidates.Count != 1) return -1;
                var gain = (SimpleVolume)candidates[0];
                float level;
                bool mute;
                gain.GetLevel(out level);
                gain.GetMute(out mute);
                int current = mute ? 0 : (int)Math.Round(level * 100);
                if (!value.HasValue) return current;
                int target = Adjust(current, value.Value, relative);
                Guid context = Guid.Empty;
                gain.SetLevel(target / 100f, ref context);
                if (mute && target > 0) gain.SetMute(false, ref context);
                return target;
            }
            catch (COMException) { return -1; }
            catch (InvalidCastException) { return -1; }
            finally { foreach (var session in matches) Marshal.ReleaseComObject(session); }
        }

        private static void Collect(AudioDevice device, string id, int userSession, List<SessionControl> matches, List<SessionControl> active)
        {
            Guid iid = typeof(SessionManager).GUID;
            SessionManager manager;
            device.Activate(ref iid, 23, IntPtr.Zero, out manager);
            try
            {
                SessionList sessions;
                manager.Enumerate(out sessions);
                try
                {
                    int count;
                    sessions.Count(out count);
                    for (int i=0; i<count; i++)
                    {
                        object entry;
                        sessions.Item(i,out entry);
                        bool keep = false;
                        try
                        {
                            var item = (SessionControl)entry;
                            uint pid; int state;
                            if (item.GetProcessId(out pid) < 0 || item.IsSystemSoundsSession() == 0 ||
                                item.GetState(out state) < 0 || state == 2 || !Matches(id,pid,userSession)) continue;
                            matches.Add(item);
                            keep = true;
                            if (state == 1) active.Add(item);
                        }
                        finally { if (!keep) Marshal.ReleaseComObject(entry); }
                    }
                }
                finally { Marshal.ReleaseComObject(sessions); }
            }
            finally { Marshal.ReleaseComObject(manager); }
        }

        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
        private static extern int GetApplicationUserModelId(IntPtr process, ref uint length, StringBuilder id);

        [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] private class MMDevices { }
        // Unused methods retain their native vtable positions.
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("A95664D2-9614-4F35-A746-DE8DB63617E6")]
        private interface DeviceEnumerator { void Endpoints(int flow, uint mask, out DeviceCollection devices); }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E")]
        private interface DeviceCollection { void Count(out uint count); void Item(uint i, out AudioDevice device); }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("D666063F-1587-4E43-81F1-B948E807363F")]
        private interface AudioDevice { void Activate(ref Guid iid,uint context,IntPtr parameters,out SessionManager manager); }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F")]
        private interface SessionManager { void SessionControl(); void SimpleVolume(); void Enumerate(out SessionList list); }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8")]
        private interface SessionList { void Count(out int count); void Item(int i, [MarshalAs(UnmanagedType.IUnknown)] out object session); }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D")]
        private interface SessionControl
        {
            [PreserveSig] int GetState(out int state);
            void GetDisplayName(); void SetDisplayName(); void GetIconPath(); void SetIconPath();
            void GetGroupingParam(); void SetGroupingParam(); void RegisterEvents(); void UnregisterEvents();
            void GetSessionIdentifier(); void GetSessionInstanceIdentifier();
            [PreserveSig] int GetProcessId(out uint pid);
            [PreserveSig] int IsSystemSoundsSession();
        }
        [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("87CE5498-68D6-44E5-9215-6DA47EF883D8")]
        private interface SimpleVolume
        {
            void SetLevel(float volume, ref Guid context); void GetLevel(out float volume);
            void SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, ref Guid context);
            void GetMute([MarshalAs(UnmanagedType.Bool)] out bool mute);
        }
    }
}
