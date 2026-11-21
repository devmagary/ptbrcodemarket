using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace DllStringPatcher
{
    internal class Program
    {
        private class SectionInfo
        {
            public int HeaderOffset;
            public string Name;
            public uint VirtualSize;
            public uint VirtualAddress;
            public uint SizeOfRawData;
            public uint PointerToRawData;
        }

        private class StreamInfo
        {
            public int EntryOffset;
            public uint RelOffset;
            public uint Size;
            public string Name;
        }

        private class UsEntry
        {
            public int OldRelOffset;
            public int NewRelOffset;
            public string Value;
            public byte[] RawUtf16;
            public byte TerminalByte;
            public List<string> Callers = new List<string>();
        }

        private class MethodDefInfo
        {
            public string DeclaringType;
            public string Name;
            public uint Rva;
            public uint MethodList;
        }

        private static int Main(string[] args)
        {
            if (args.Length < 1)
            {
                PrintHelp();
                return 1;
            }
            string cmd = args[0].ToLowerInvariant();
            try
            {
                if (cmd == "extract" && args.Length == 4)
                {
                    Extract(args[1], args[2], args[3] == "--pretty");
                    return 0;
                }
                if (cmd == "extract" && args.Length == 3)
                {
                    Extract(args[1], args[2], false);
                    return 0;
                }
                if (cmd == "patch" && args.Length == 4)
                {
                    Patch(args[1], args[2], args[3]);
                    return 0;
                }
                PrintHelp();
                return 1;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("ERROR: " + ex.ToString());
                return 2;
            }
        }

        private static void PrintHelp()
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  DllStringPatcher extract <dll_path> <out_json_path>");
            Console.WriteLine("  DllStringPatcher patch <dll_path> <patch_json_path> <out_dll_path>");
        }

        private static ushort ReadU16(byte[] b, int o) { return (ushort)(b[o] | (b[o + 1] << 8)); }
        private static uint ReadU32(byte[] b, int o) { return (uint)(b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)); }
        private static ulong ReadU64(byte[] b, int o) { return ReadU32(b, o) | ((ulong)ReadU32(b, o + 4) << 32); }

        private static void WriteU16(byte[] b, int o, ushort v)
        {
            b[o] = (byte)(v & 0xFF);
            b[o + 1] = (byte)((v >> 8) & 0xFF);
        }

        private static void WriteU32(byte[] b, int o, uint v)
        {
            b[o] = (byte)(v & 0xFF);
            b[o + 1] = (byte)((v >> 8) & 0xFF);
            b[o + 2] = (byte)((v >> 16) & 0xFF);
            b[o + 3] = (byte)((v >> 24) & 0xFF);
        }

        private static uint AlignUp(uint val, uint align)
        {
            return (val + align - 1) & ~(align - 1);
        }

        private static int RvaToOffset(List<SectionInfo> sections, uint rva)
        {
            for (int i = 0; i < sections.Count; i++)
            {
                SectionInfo s = sections[i];
                uint span = Math.Max(s.VirtualSize, s.SizeOfRawData);
                if (rva >= s.VirtualAddress && rva < s.VirtualAddress + span)
                    return (int)(s.PointerToRawData + (rva - s.VirtualAddress));
            }
            return -1;
        }

        private static void ParsePeAndMeta(
            byte[] data,
            out int peOff,
            out int optOff,
            out int dataDirOff,
            out uint sectionAlign,
            out uint fileAlign,
            out List<SectionInfo> sections,
            out int cliOff,
            out int metaOff,
            out uint metaSize,
            out int streamHeaderPos,
            out List<StreamInfo> streams)
        {
            peOff = (int)ReadU32(data, 0x3C);
            ushort numSec = ReadU16(data, peOff + 6);
            ushort optSize = ReadU16(data, peOff + 20);
            optOff = peOff + 24;
            ushort magic = ReadU16(data, optOff);
            sectionAlign = ReadU32(data, optOff + 32);
            fileAlign = ReadU32(data, optOff + 36);
            dataDirOff = optOff + (magic == 0x10B ? 96 : 112);

            sections = new List<SectionInfo>();
            int secOff = optOff + optSize;
            for (int i = 0; i < numSec; i++)
            {
                int ho = secOff + i * 40;
                string name = Encoding.ASCII.GetString(data, ho, 8).TrimEnd('\0');
                sections.Add(new SectionInfo
                {
                    HeaderOffset = ho,
                    Name = name,
                    VirtualSize = ReadU32(data, ho + 8),
                    VirtualAddress = ReadU32(data, ho + 12),
                    SizeOfRawData = ReadU32(data, ho + 16),
                    PointerToRawData = ReadU32(data, ho + 20)
                });
            }

            uint cliRva = ReadU32(data, dataDirOff + 14 * 8);
            cliOff = RvaToOffset(sections, cliRva);
            uint metaRva = ReadU32(data, cliOff + 8);
            metaSize = ReadU32(data, cliOff + 12);
            metaOff = RvaToOffset(sections, metaRva);

            uint verLen = ReadU32(data, metaOff + 12);
            int pos = metaOff + 16 + (int)verLen + 2;
            ushort numStreams = ReadU16(data, pos);
            pos += 2;
            streamHeaderPos = pos;

            streams = new List<StreamInfo>();
            for (int i = 0; i < numStreams; i++)
            {
                int entryOff = pos;
                uint sOff = ReadU32(data, pos);
                uint sSz = ReadU32(data, pos + 4);
                pos += 8;
                int nameStart = pos;
                while (data[pos] != 0) pos++;
                string sName = Encoding.ASCII.GetString(data, nameStart, pos - nameStart);
                pos = (pos + 4) & ~3;
                streams.Add(new StreamInfo
                {
                    EntryOffset = entryOff,
                    RelOffset = sOff,
                    Size = sSz,
                    Name = sName
                });
            }
        }

        private static StreamInfo FindStream(List<StreamInfo> streams, string name)
        {
            for (int i = 0; i < streams.Count; i++)
                if (streams[i].Name == name)
                    return streams[i];
            throw new InvalidOperationException("Stream not found: " + name);
        }

        private static List<MethodDefInfo> ParseMethods(byte[] data, int metaOff, List<StreamInfo> streams)
        {
            StreamInfo tStream = FindStream(streams, "#~");
            StreamInfo sStream = FindStream(streams, "#Strings");
            int tOff = metaOff + (int)tStream.RelOffset;
            int strOff = metaOff + (int)sStream.RelOffset;

            byte heapSizes = data[tOff + 6];
            ulong validMask = ReadU64(data, tOff + 8);
            int pos = tOff + 24;
            uint[] rc = new uint[64];
            for (int i = 0; i < 64; i++)
            {
                if (((validMask >> i) & 1UL) != 0)
                {
                    rc[i] = ReadU32(data, pos);
                    pos += 4;
                }
            }

            int strIdx = (heapSizes & 1) != 0 ? 4 : 2;
            int guidIdx = (heapSizes & 2) != 0 ? 4 : 2;
            int blobIdx = (heapSizes & 4) != 0 ? 4 : 2;
            int fieldIdx = rc[4] >= 65536 ? 4 : 2;
            int methodIdx = rc[6] >= 65536 ? 4 : 2;
            int paramIdx = rc[8] >= 65536 ? 4 : 2;
            int resScopeIdx = (rc[0] >= 16384 || rc[0x1A] >= 16384 || rc[0x23] >= 16384 || rc[1] >= 16384) ? 4 : 2;
            int typeDefOrRefIdx = (rc[2] >= 16384 || rc[1] >= 16384 || rc[0x1B] >= 16384) ? 4 : 2;

            // 0x00 Module
            pos += (int)rc[0] * (2 + strIdx + guidIdx * 3);
            // 0x01 TypeRef
            pos += (int)rc[1] * (resScopeIdx + strIdx * 2);

            // 0x02 TypeDef
            var typeNames = new List<string>();
            var typeFirstMethod = new List<uint>();
            int tdRowSz = 4 + strIdx * 2 + typeDefOrRefIdx + fieldIdx + methodIdx;
            for (uint i = 0; i < rc[2]; i++)
            {
                uint nameI = strIdx == 4 ? ReadU32(data, pos + 4) : ReadU16(data, pos + 4);
                uint nsI = strIdx == 4 ? ReadU32(data, pos + 4 + strIdx) : ReadU16(data, pos + 4 + strIdx);
                uint mList = methodIdx == 4 ? ReadU32(data, pos + 4 + strIdx * 2 + typeDefOrRefIdx + fieldIdx)
                                            : ReadU16(data, pos + 4 + strIdx * 2 + typeDefOrRefIdx + fieldIdx);
                string tName = ReadUtf8Z(data, strOff + (int)nameI);
                string ns = ReadUtf8Z(data, strOff + (int)nsI);
                typeNames.Add(string.IsNullOrEmpty(ns) ? tName : (ns + "." + tName));
                typeFirstMethod.Add(mList);
                pos += tdRowSz;
            }

            // 0x03 FieldPtr (if any)
            pos += (int)rc[3] * fieldIdx;
            // 0x04 Field
            pos += (int)rc[4] * (2 + strIdx + blobIdx);
            // 0x05 MethodPtr (if any)
            pos += (int)rc[5] * methodIdx;

            // 0x06 MethodDef
            var methods = new List<MethodDefInfo>();
            int mdRowSz = 4 + 2 + 2 + strIdx + blobIdx + paramIdx;
            int typeIdx = 0;
            for (uint m = 1; m <= rc[6]; m++)
            {
                while (typeIdx + 1 < typeFirstMethod.Count && typeFirstMethod[typeIdx + 1] <= m)
                    typeIdx++;
                uint rva = ReadU32(data, pos);
                uint nameI = strIdx == 4 ? ReadU32(data, pos + 8) : ReadU16(data, pos + 8);
                string mName = ReadUtf8Z(data, strOff + (int)nameI);
                methods.Add(new MethodDefInfo
                {
                    DeclaringType = typeIdx < typeNames.Count ? typeNames[typeIdx] : "",
                    Name = mName,
                    Rva = rva
                });
                pos += mdRowSz;
            }
            return methods;
        }

        private static string ReadUtf8Z(byte[] data, int off)
        {
            int end = off;
            while (end < data.Length && data[end] != 0) end++;
            return Encoding.UTF8.GetString(data, off, end - off);
        }

        private static int SingleByteOperandSize(byte op)
        {
            switch (op)
            {
                case 0x0E: case 0x0F: case 0x10: case 0x11: case 0x12: case 0x13:
                case 0x1F:
                case 0x2B: case 0x2C: case 0x2D: case 0x2E: case 0x2F: case 0x30:
                case 0x31: case 0x32: case 0x33: case 0x34: case 0x35: case 0x36: case 0x37:
                case 0xDE:
                    return 1;
                case 0x20: case 0x22:
                case 0x27: case 0x28: case 0x29:
                case 0x38: case 0x39: case 0x3A: case 0x3B: case 0x3C: case 0x3D:
                case 0x3E: case 0x3F: case 0x40: case 0x41: case 0x42: case 0x43: case 0x44:
                case 0x6F: case 0x70: case 0x71: case 0x72: case 0x73: case 0x74: case 0x75:
                case 0x79:
                case 0x7B: case 0x7C: case 0x7D: case 0x7E: case 0x7F: case 0x80: case 0x81:
                case 0x8C: case 0x8D: case 0x8F:
                case 0xA3: case 0xA4: case 0xA5:
                case 0xC2: case 0xC6:
                case 0xD0:
                case 0xDD:
                    return 4;
                case 0x21: case 0x23:
                    return 8;
                default:
                    return 0;
            }
        }

        private static int TwoByteOperandSize(byte op2)
        {
            switch (op2)
            {
                case 0x09: case 0x0A: case 0x0B: case 0x0C: case 0x0D: case 0x0E:
                    return 2;
                case 0x12:
                    return 1;
                case 0x06: case 0x07: case 0x15: case 0x16: case 0x1C:
                    return 4;
                default:
                    return 0;
            }
        }

        private static void ScanMethodLdstr(
            byte[] data,
            List<SectionInfo> sections,
            List<MethodDefInfo> methods,
            Action<MethodDefInfo, int, int> onLdstr)
        {
            for (int i = 0; i < methods.Count; i++)
            {
                MethodDefInfo m = methods[i];
                if (m.Rva == 0) continue;
                int off = RvaToOffset(sections, m.Rva);
                if (off < 0) continue;
                byte b0 = data[off];
                int codeOff;
                int codeSize;
                if ((b0 & 3) == 2)
                {
                    codeOff = off + 1;
                    codeSize = b0 >> 2;
                }
                else if ((b0 & 3) == 3)
                {
                    codeOff = off + ((data[off + 1] >> 4) * 4);
                    codeSize = (int)ReadU32(data, off + 4);
                }
                else
                {
                    continue;
                }

                int ip = codeOff;
                int end = codeOff + codeSize;
                while (ip < end)
                {
                    byte op = data[ip];
                    if (op == 0xFE && ip + 1 < end)
                    {
                        byte op2 = data[ip + 1];
                        ip += 2 + TwoByteOperandSize(op2);
                    }
                    else if (op == 0x45)
                    {
                        uint count = ReadU32(data, ip + 1);
                        ip += 5 + (int)count * 4;
                    }
                    else
                    {
                        if (op == 0x72 && ip + 5 <= end)
                        {
                            uint tok = ReadU32(data, ip + 1);
                            if ((tok >> 24) == 0x70)
                            {
                                onLdstr(m, ip + 1, (int)(tok & 0x00FFFFFF));
                            }
                        }
                        ip += 1 + SingleByteOperandSize(op);
                    }
                }
            }
        }

        private static List<UsEntry> ReadUsEntries(byte[] data, int usOff, int usSize)
        {
            var list = new List<UsEntry>();
            int pos = usOff + 1;
            int end = usOff + usSize;
            while (pos < end)
            {
                int rel = pos - usOff;
                byte b0 = data[pos];
                if (b0 == 0)
                {
                    pos++;
                    continue;
                }
                int len;
                if ((b0 & 0x80) == 0)
                {
                    len = b0;
                    pos += 1;
                }
                else if ((b0 & 0xC0) == 0x80)
                {
                    len = ((b0 & 0x3F) << 8) | data[pos + 1];
                    pos += 2;
                }
                else
                {
                    len = ((b0 & 0x1F) << 24) | (data[pos + 1] << 16) | (data[pos + 2] << 8) | data[pos + 3];
                    pos += 4;
                }
                if (len > 0)
                {
                    int strByteLen = len - 1;
                    byte[] raw = new byte[strByteLen];
                    Buffer.BlockCopy(data, pos, raw, 0, strByteLen);
                    byte term = data[pos + strByteLen];
                    string val = Encoding.Unicode.GetString(raw);
                    list.Add(new UsEntry
                    {
                        OldRelOffset = rel,
                        Value = val,
                        RawUtf16 = raw,
                        TerminalByte = term
                    });
                }
                pos += len;
            }
            return list;
        }

        private static byte ComputeEcmaTerminalByte(string s)
        {
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                if ((c >> 8) != 0) return 1;
                byte lo = (byte)(c & 0xFF);
                if ((lo >= 0x01 && lo <= 0x08) || (lo >= 0x0E && lo <= 0x1F) || lo == 0x27 || lo == 0x2D || lo == 0x7F)
                    return 1;
            }
            return 0;
        }

        private static void WriteCompressedUint(MemoryStream ms, uint v)
        {
            if (v <= 0x7F)
            {
                ms.WriteByte((byte)v);
            }
            else if (v <= 0x3FFF)
            {
                ms.WriteByte((byte)((v >> 8) | 0x80));
                ms.WriteByte((byte)(v & 0xFF));
            }
            else
            {
                ms.WriteByte((byte)((v >> 24) | 0xC0));
                ms.WriteByte((byte)((v >> 16) & 0xFF));
                ms.WriteByte((byte)((v >> 8) & 0xFF));
                ms.WriteByte((byte)(v & 0xFF));
            }
        }

        private static void Extract(string dllPath, string outJsonPath, bool pretty)
        {
            byte[] data = File.ReadAllBytes(dllPath);
            int peOff, optOff, dataDirOff, cliOff, metaOff, streamHeaderPos;
            uint secAlign, fileAlign, metaSize;
            List<SectionInfo> sections;
            List<StreamInfo> streams;
            ParsePeAndMeta(data, out peOff, out optOff, out dataDirOff, out secAlign, out fileAlign,
                out sections, out cliOff, out metaOff, out metaSize, out streamHeaderPos, out streams);

            StreamInfo usStream = FindStream(streams, "#US");
            var entries = ReadUsEntries(data, metaOff + (int)usStream.RelOffset, (int)usStream.Size);
            var byOffset = new Dictionary<int, UsEntry>();
            for (int i = 0; i < entries.Count; i++)
                byOffset[entries[i].OldRelOffset] = entries[i];

            var methods = ParseMethods(data, metaOff, streams);
            ScanMethodLdstr(data, sections, methods, (m, operandOff, usRel) =>
            {
                UsEntry e;
                if (byOffset.TryGetValue(usRel, out e))
                {
                    string sig = m.DeclaringType + "::" + m.Name;
                    if (!e.Callers.Contains(sig))
                        e.Callers.Add(sig);
                }
            });

            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"dll\": \"").Append(JsonEscape(Path.GetFileName(dllPath))).Append("\",\n");
            sb.Append("  \"us_count\": ").Append(entries.Count).Append(",\n");
            sb.Append("  \"strings\": [\n");
            for (int i = 0; i < entries.Count; i++)
            {
                UsEntry e = entries[i];
                sb.Append("    {\"us_offset\": ").Append(e.OldRelOffset);
                sb.Append(", \"token\": \"0x").Append((0x70000000 | (uint)e.OldRelOffset).ToString("x8")).Append("\"");
                sb.Append(", \"value\": \"").Append(JsonEscape(e.Value)).Append("\"");
                sb.Append(", \"callers\": [");
                for (int c = 0; c < e.Callers.Count; c++)
                {
                    if (c > 0) sb.Append(", ");
                    sb.Append("\"").Append(JsonEscape(e.Callers[c])).Append("\"");
                }
                sb.Append("]}");
                if (i + 1 < entries.Count) sb.Append(",");
                sb.Append("\n");
            }
            sb.Append("  ]\n}\n");
            File.WriteAllText(outJsonPath, sb.ToString(), new UTF8Encoding(false));
        }

        private static void Patch(string dllPath, string patchJsonPath, string outDllPath)
        {
            byte[] orig = File.ReadAllBytes(dllPath);
            Dictionary<int, string> patchMap = ParsePatchJson(File.ReadAllText(patchJsonPath, Encoding.UTF8));

            int peOff, optOff, dataDirOff, cliOff, metaOff, streamHeaderPos;
            uint secAlign, fileAlign, oldMetaSize;
            List<SectionInfo> sections;
            List<StreamInfo> streams;
            ParsePeAndMeta(orig, out peOff, out optOff, out dataDirOff, out secAlign, out fileAlign,
                out sections, out cliOff, out metaOff, out oldMetaSize, out streamHeaderPos, out streams);

            StreamInfo usStream = FindStream(streams, "#US");
            var entries = ReadUsEntries(orig, metaOff + (int)usStream.RelOffset, (int)usStream.Size);

            // Rebuild #US stream
            var usMs = new MemoryStream();
            usMs.WriteByte(0); // mandatory initial null byte
            var offsetMap = new Dictionary<int, int>();
            for (int i = 0; i < entries.Count; i++)
            {
                UsEntry e = entries[i];
                int newRel = (int)usMs.Position;
                offsetMap[e.OldRelOffset] = newRel;
                string newVal;
                byte[] utf16;
                byte term;
                if (patchMap.TryGetValue(e.OldRelOffset, out newVal))
                {
                    utf16 = Encoding.Unicode.GetBytes(newVal);
                    term = ComputeEcmaTerminalByte(newVal);
                }
                else
                {
                    utf16 = e.RawUtf16;
                    term = ComputeEcmaTerminalByte(e.Value);
                }
                WriteCompressedUint(usMs, (uint)(utf16.Length + 1));
                usMs.Write(utf16, 0, utf16.Length);
                usMs.WriteByte(term);
            }
            while ((usMs.Position % 4) != 0) usMs.WriteByte(0);
            byte[] newUs = usMs.ToArray();

            // Rebuild Metadata Root preserving stream order
            int headerBytesLen = (metaOff + (int)streams[0].RelOffset) - metaOff;
            var metaMs = new MemoryStream();
            metaMs.Write(orig, metaOff, headerBytesLen);

            uint curRel = (uint)headerBytesLen;
            var newStreamRelOffsets = new uint[streams.Count];
            var newStreamSizes = new uint[streams.Count];
            for (int i = 0; i < streams.Count; i++)
            {
                StreamInfo s = streams[i];
                newStreamRelOffsets[i] = curRel;
                if (s.Name == "#US")
                {
                    metaMs.Write(newUs, 0, newUs.Length);
                    newStreamSizes[i] = (uint)newUs.Length;
                    curRel += (uint)newUs.Length;
                }
                else
                {
                    int absOff = metaOff + (int)s.RelOffset;
                    metaMs.Write(orig, absOff, (int)s.Size);
                    newStreamSizes[i] = s.Size;
                    curRel += s.Size;
                }
            }
            while ((metaMs.Position % 4) != 0) metaMs.WriteByte(0);
            byte[] newMeta = metaMs.ToArray();

            // Patch stream headers inside newMeta
            for (int i = 0; i < streams.Count; i++)
            {
                int relEntryOff = streams[i].EntryOffset - metaOff;
                WriteU32(newMeta, relEntryOff, newStreamRelOffsets[i]);
                WriteU32(newMeta, relEntryOff + 4, newStreamSizes[i]);
            }

            // Prepare output PE buffer
            byte[] work = (byte[])orig.Clone();
            var methods = ParseMethods(orig, metaOff, streams);
            ScanMethodLdstr(work, sections, methods, (m, operandOff, oldUsRel) =>
            {
                int newUsRel;
                if (offsetMap.TryGetValue(oldUsRel, out newUsRel) && newUsRel != oldUsRel)
                {
                    WriteU32(work, operandOff, 0x70000000U | (uint)newUsRel);
                }
            });

            uint newMetaSize = (uint)newMeta.Length;
            byte[] finalPe;
            if (newMetaSize <= oldMetaSize)
            {
                finalPe = work;
                Buffer.BlockCopy(newMeta, 0, finalPe, metaOff, newMeta.Length);
                for (int i = metaOff + newMeta.Length; i < metaOff + (int)oldMetaSize; i++)
                    finalPe[i] = 0;
                WriteU32(finalPe, cliOff + 12, newMetaSize);
            }
            else
            {
                int delta = (int)(newMetaSize - oldMetaSize);
                uint oldMetaEndRva = ReadU32(orig, cliOff + 8) + oldMetaSize;
                for (int si = 0; si < streams.Count; si++)
                {
                    if (streams[si].Name == "#~")
                    {
                        ShiftFieldRvas(newMeta, (int)newStreamRelOffsets[si], oldMetaEndRva, (uint)delta);
                        break;
                    }
                }
                SectionInfo textSec = sections[0];
                int oldMetaEnd = metaOff + (int)oldMetaSize;
                int oldTextRawEnd = (int)(textSec.PointerToRawData + textSec.SizeOfRawData);
                int oldTextUsedEnd = (int)(textSec.PointerToRawData + textSec.VirtualSize);
                int tailUsedLen = Math.Max(0, oldTextUsedEnd - oldMetaEnd);
                if (tailUsedLen == 0) tailUsedLen = oldTextRawEnd - oldMetaEnd;

                int newTextUsedSize = (metaOff - (int)textSec.PointerToRawData) + (int)newMetaSize + tailUsedLen;
                uint newTextRawSize = AlignUp((uint)newTextUsedSize, fileAlign);
                uint rawGrowth = newTextRawSize - textSec.SizeOfRawData;

                // Determine virtual shift for subsequent sections if needed
                uint textEndRva = textSec.VirtualAddress + (uint)newTextUsedSize;
                uint virtShift = 0;
                if (sections.Count > 1 && textEndRva > sections[1].VirtualAddress)
                {
                    uint nextSecRva = AlignUp(textEndRva, secAlign);
                    virtShift = nextSecRva - sections[1].VirtualAddress;
                }

                finalPe = new byte[work.Length + (int)rawGrowth];
                // Copy up to metaOff
                Buffer.BlockCopy(work, 0, finalPe, 0, metaOff);
                // Write new metadata
                Buffer.BlockCopy(newMeta, 0, finalPe, metaOff, newMeta.Length);
                // Copy shifted tail of .text
                Buffer.BlockCopy(work, oldMetaEnd, finalPe, metaOff + newMeta.Length, tailUsedLen);
                // Copy remaining sections (.rsrc, .reloc, etc.)
                if (sections.Count > 1)
                {
                    int srcAfterText = (int)sections[1].PointerToRawData;
                    int dstAfterText = (int)(sections[1].PointerToRawData + rawGrowth);
                    Buffer.BlockCopy(work, srcAfterText, finalPe, dstAfterText, work.Length - srcAfterText);
                }

                // Update CLI MetaData size
                WriteU32(finalPe, cliOff + 12, newMetaSize);

                // Update AddressOfEntryPoint
                uint epRva = ReadU32(finalPe, optOff + 16);
                uint epNewRva = epRva + (uint)delta;
                WriteU32(finalPe, optOff + 16, epNewRva);

                // Update Debug Directory (DataDir[6])
                uint dbgRva = ReadU32(finalPe, dataDirOff + 6 * 8);
                uint dbgSize = ReadU32(finalPe, dataDirOff + 6 * 8 + 4);
                if (dbgRva != 0 && dbgSize != 0)
                {
                    WriteU32(finalPe, dataDirOff + 6 * 8, dbgRva + (uint)delta);
                    int dbgOff = metaOff + newMeta.Length + (RvaToOffset(sections, dbgRva) - oldMetaEnd);
                    for (int off = 0; off + 28 <= dbgSize; off += 28)
                    {
                        uint addrRaw = ReadU32(finalPe, dbgOff + off + 20);
                        uint ptrRaw = ReadU32(finalPe, dbgOff + off + 24);
                        if (addrRaw != 0) WriteU32(finalPe, dbgOff + off + 20, addrRaw + (uint)delta);
                        if (ptrRaw != 0) WriteU32(finalPe, dbgOff + off + 24, ptrRaw + (uint)delta);
                    }
                }

                // Update Import Directory (DataDir[1])
                uint impRva = ReadU32(finalPe, dataDirOff + 1 * 8);
                if (impRva != 0)
                {
                    WriteU32(finalPe, dataDirOff + 1 * 8, impRva + (uint)delta);
                    int impOff = metaOff + newMeta.Length + (RvaToOffset(sections, impRva) - oldMetaEnd);
                    uint iltRva = ReadU32(finalPe, impOff);
                    uint nameRva = ReadU32(finalPe, impOff + 12);
                    if (iltRva != 0)
                    {
                        WriteU32(finalPe, impOff, iltRva + (uint)delta);
                        int iltOff = metaOff + newMeta.Length + (RvaToOffset(sections, iltRva) - oldMetaEnd);
                        uint hintRva = ReadU32(finalPe, iltOff);
                        if (hintRva != 0 && (hintRva & 0x80000000U) == 0)
                            WriteU32(finalPe, iltOff, hintRva + (uint)delta);
                    }
                    if (nameRva != 0)
                        WriteU32(finalPe, impOff + 12, nameRva + (uint)delta);
                }

                // Update .text section header
                WriteU32(finalPe, textSec.HeaderOffset + 8, (uint)newTextUsedSize);
                WriteU32(finalPe, textSec.HeaderOffset + 16, newTextRawSize);

                // Update subsequent sections (.rsrc, .reloc)
                for (int i = 1; i < sections.Count; i++)
                {
                    SectionInfo s = sections[i];
                    uint newRawPtr = s.PointerToRawData + rawGrowth;
                    uint newVirtAddr = s.VirtualAddress + virtShift;
                    WriteU32(finalPe, s.HeaderOffset + 12, newVirtAddr);
                    WriteU32(finalPe, s.HeaderOffset + 20, newRawPtr);

                    if (s.Name == ".rsrc" && virtShift != 0)
                    {
                        uint rsrcRva = ReadU32(finalPe, dataDirOff + 2 * 8);
                        if (rsrcRva != 0) WriteU32(finalPe, dataDirOff + 2 * 8, rsrcRva + virtShift);
                        ShiftRsrcRvas(finalPe, (int)newRawPtr, (int)newRawPtr, virtShift);
                    }
                    if (s.Name == ".reloc")
                    {
                        uint relocRva = ReadU32(finalPe, dataDirOff + 5 * 8);
                        if (relocRva != 0) WriteU32(finalPe, dataDirOff + 5 * 8, relocRva + virtShift);
                        // Update base relocation entry for EntryPoint jmp dword ptr [IAT]
                        uint pageRva = (epNewRva + 2) & ~0xFFFU;
                        ushort entry = (ushort)(0x3000U | ((epNewRva + 2) & 0xFFFU));
                        WriteU32(finalPe, (int)newRawPtr, pageRva);
                        WriteU16(finalPe, (int)newRawPtr + 8, entry);
                    }
                }

                // Update SizeOfCode & SizeOfImage
                WriteU32(finalPe, optOff + 4, newTextRawSize);
                if (sections.Count > 0)
                {
                    SectionInfo last = sections[sections.Count - 1];
                    uint lastVirt = last.VirtualAddress + virtShift;
                    uint sizeOfImage = AlignUp(lastVirt + last.VirtualSize, secAlign);
                    WriteU32(finalPe, optOff + 56, sizeOfImage);
                }
            }

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outDllPath)));
            File.WriteAllBytes(outDllPath, finalPe);
        }

        private static void ShiftFieldRvas(byte[] meta, int tOff, uint oldMetaEndRva, uint delta)
        {
            byte heapSizes = meta[tOff + 6];
            ulong validMask = ReadU64(meta, tOff + 8);
            int p = tOff + 24;
            uint[] rc = new uint[64];
            for (int i = 0; i < 64; i++)
            {
                if (((validMask >> i) & 1UL) != 0)
                {
                    rc[i] = ReadU32(meta, p);
                    p += 4;
                }
            }
            if (rc[0x1D] == 0) return;

            int S = (heapSizes & 1) != 0 ? 4 : 2;
            int G = (heapSizes & 2) != 0 ? 4 : 2;
            int B = (heapSizes & 4) != 0 ? 4 : 2;
            Func<int, int> tidx = t => rc[t] >= 65536 ? 4 : 2;
            Func<int, int[], int> coded = (bits, tbls) =>
            {
                uint limit = 1U << (16 - bits);
                for (int k = 0; k < tbls.Length; k++)
                    if (rc[tbls[k]] >= limit) return 4;
                return 2;
            };

            int TypeDefOrRef = coded(2, new[] { 2, 1, 0x1B });
            int HasConstant = coded(2, new[] { 4, 8, 0x17 });
            int HasCustomAttr = coded(5, new[] { 6, 4, 1, 2, 8, 9, 10, 0, 0xE, 0x17, 0x14, 0x11, 0x1A, 0x1B, 0x20, 0x23, 0x26, 0x27, 0x28 });
            int HasFieldMarshal = coded(1, new[] { 4, 8 });
            int HasDeclSecurity = coded(2, new[] { 2, 6, 0x20 });
            int MemberRefParent = coded(3, new[] { 2, 1, 0x1A, 6, 0x1B });
            int HasSemantics = coded(1, new[] { 0x14, 0x17 });
            int MethodDefOrRef = coded(1, new[] { 6, 10 });
            int MemberForwarded = coded(1, new[] { 4, 6 });
            int CustomAttrType = coded(3, new[] { 6, 10 });
            int ResolutionScope = coded(2, new[] { 0, 0x1A, 0x23, 1 });

            int[] rowSizes = new int[0x1E];
            rowSizes[0x00] = 2 + S + 3 * G;
            rowSizes[0x01] = ResolutionScope + 2 * S;
            rowSizes[0x02] = 4 + 2 * S + TypeDefOrRef + tidx(4) + tidx(6);
            rowSizes[0x03] = tidx(4);
            rowSizes[0x04] = 2 + S + B;
            rowSizes[0x05] = tidx(6);
            rowSizes[0x06] = 4 + 2 + 2 + S + B + tidx(8);
            rowSizes[0x07] = tidx(8);
            rowSizes[0x08] = 2 + 2 + S;
            rowSizes[0x09] = tidx(2) + TypeDefOrRef;
            rowSizes[0x0A] = MemberRefParent + S + B;
            rowSizes[0x0B] = 2 + HasConstant + B;
            rowSizes[0x0C] = HasCustomAttr + CustomAttrType + B;
            rowSizes[0x0D] = HasFieldMarshal + B;
            rowSizes[0x0E] = 2 + HasDeclSecurity + B;
            rowSizes[0x0F] = 2 + 4 + tidx(2);
            rowSizes[0x10] = 4 + tidx(4);
            rowSizes[0x11] = B;
            rowSizes[0x12] = tidx(2) + tidx(0x14);
            rowSizes[0x13] = tidx(0x14);
            rowSizes[0x14] = 2 + S + TypeDefOrRef;
            rowSizes[0x15] = tidx(2) + tidx(0x17);
            rowSizes[0x16] = tidx(0x17);
            rowSizes[0x17] = 2 + S + B;
            rowSizes[0x18] = 2 + tidx(6) + HasSemantics;
            rowSizes[0x19] = tidx(2) + MethodDefOrRef + MethodDefOrRef;
            rowSizes[0x1A] = S;
            rowSizes[0x1B] = B;
            rowSizes[0x1C] = 2 + MemberForwarded + S + tidx(0x1A);
            rowSizes[0x1D] = 4 + tidx(4);

            for (int t = 0; t < 0x1D; t++)
                p += (int)rc[t] * rowSizes[t];

            for (uint i = 0; i < rc[0x1D]; i++)
            {
                int rowOff = p + (int)i * rowSizes[0x1D];
                uint rva = ReadU32(meta, rowOff);
                if (rva >= oldMetaEndRva)
                    WriteU32(meta, rowOff, rva + delta);
            }
        }

        private static void ShiftRsrcRvas(byte[] pe, int rsrcBase, int dirOff, uint virtShift)
        {
            ushort namedCount = ReadU16(pe, dirOff + 12);
            ushort idCount = ReadU16(pe, dirOff + 14);
            int total = namedCount + idCount;
            int entryPos = dirOff + 16;
            for (int i = 0; i < total; i++)
            {
                uint offToData = ReadU32(pe, entryPos + 4);
                if ((offToData & 0x80000000U) != 0)
                {
                    ShiftRsrcRvas(pe, rsrcBase, rsrcBase + (int)(offToData & 0x7FFFFFFFU), virtShift);
                }
                else
                {
                    int dataEntryOff = rsrcBase + (int)offToData;
                    uint rva = ReadU32(pe, dataEntryOff);
                    WriteU32(pe, dataEntryOff, rva + virtShift);
                }
                entryPos += 8;
            }
        }

        private static string JsonEscape(string s)
        {
            var sb = new StringBuilder(s.Length + 8);
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                switch (c)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '"': sb.Append("\\\""); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20 || c == 0x7F)
                            sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else
                            sb.Append(c);
                        break;
                }
            }
            return sb.ToString();
        }

        private static Dictionary<int, string> ParsePatchJson(string json)
        {
            var map = new Dictionary<int, string>();
            int i = 0;
            SkipWs(json, ref i);
            if (i >= json.Length || json[i] != '{')
                throw new InvalidDataException("Expected JSON object in patch file");
            i++;
            while (i < json.Length)
            {
                SkipWs(json, ref i);
                if (i < json.Length && json[i] == '}') break;
                if (json[i] == ',') { i++; continue; }
                string key = ReadJsonString(json, ref i);
                SkipWs(json, ref i);
                if (json[i] != ':') throw new InvalidDataException("Expected ':' in patch JSON");
                i++;
                SkipWs(json, ref i);
                string val = ReadJsonString(json, ref i);
                map[int.Parse(key)] = val;
            }
            return map;
        }

        private static void SkipWs(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        private static string ReadJsonString(string s, ref int i)
        {
            if (s[i] != '"') throw new InvalidDataException("Expected '\"' at " + i);
            i++;
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c == '\\')
                {
                    char esc = s[i++];
                    switch (esc)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            int code = Convert.ToInt32(s.Substring(i, 4), 16);
                            sb.Append((char)code);
                            i += 4;
                            break;
                        default:
                            sb.Append(esc);
                            break;
                    }
                }
                else
                {
                    sb.Append(c);
                }
            }
            throw new InvalidDataException("Unterminated JSON string");
        }
    }
}
