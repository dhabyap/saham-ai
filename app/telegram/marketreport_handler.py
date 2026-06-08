    async def marketreport_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hidden handler — show latest @creativetrader report + AI analysis."""
        try:
            await update.message.reply_text("📊 Ambil laporan pasar terbaru...")

            import json, os
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            reports_file = os.path.join(base, "market_reports.json")

            if not os.path.exists(reports_file):
                await update.message.reply_text("❌ Belum ada data laporan. Jalankan scraper dulu.")
                return

            with open(reports_file) as f:
                reports = json.load(f)

            if not reports:
                await update.message.reply_text("❌ Laporan kosong.")
                return

            # Latest report
            latest = reports[0]
            date = latest.get('date', '?')
            ihsg = latest.get('ihsg_change')
            fb = latest.get('foreign_buy', [])
            lb = latest.get('local_buy', [])
            gainers = latest.get('gainer', [])
            losers = latest.get('loser', [])

            ihsg_str = f"{ihsg:+.2f}%" if ihsg is not None else "N/A"
            ihsg_icon = "🟢" if (ihsg or 0) >= 0 else "🔴"

            # Build message
            msg = f"{ihsg_icon} *Market Report* — {date}\n"
            msg += f"IHSG: {ihsg_str}\n\n"

            # Top Foreign Buy
            if fb:
                msg += "*🌍 Top Foreign Buy:*\n"
                for s in fb[:5]:
                    val = s['value']
                    if val >= 1e12:
                        val_str = f"{val/1e12:.2f}T"
                    elif val >= 1e9:
                        val_str = f"{val/1e9:.2f}M"
                    else:
                        val_str = f"{val/1e6:.0f}Jt"
                    msg += f"  {s['stock']}: Rp{val_str}\n"
                msg += "\n"

            # Top Local Buy
            if lb:
                msg += "*🏠 Top Local Buy:*\n"
                for s in lb[:5]:
                    val = s['value']
                    if val >= 1e12:
                        val_str = f"{val/1e12:.2f}T"
                    elif val >= 1e9:
                        val_str = f"{val/1e9:.2f}M"
                    else:
                        val_str = f"{val/1e6:.0f}Jt"
                    msg += f"  {s['stock']}: Rp{val_str}\n"
                msg += "\n"

            # Gainers
            if gainers:
                msg += "*📈 Top Gainer:*\n"
                for g in gainers[:3]:
                    msg += f"  {g['stock']}: {g['change_pct']:+.1f}%\n"
            # Losers
            if losers:
                msg += "*📉 Top Loser:*\n"
                for l in losers[:3]:
                    msg += f"  {l['stock']}: {l['change_pct']:+.1f}%\n"
            msg += "\n"

            # ── AI Analysis ──
            from collections import Counter, defaultdict
            ihsg_vals = [r['ihsg_change'] for r in reports if r['ihsg_change'] is not None]
            total = len(reports)
            red = sum(1 for v in ihsg_vals if v < 0)
            green = sum(1 for v in ihsg_vals if v > 0)
            avg = sum(ihsg_vals) / len(ihsg_vals) if ihsg_vals else 0

            # Top stocks by foreign buy frequency
            foreign_freq = Counter()
            for r in reports:
                for s in r.get('foreign_buy', []):
                    foreign_freq[s['stock']] += 1
            top_fb_stocks = foreign_freq.most_common(5)

            msg += f"*📊 Analisis ({total} laporan)*\n"
            msg += f"Rata-rata IHSG: {avg:+.2f}%\n"
            msg += f"Hijau/Merah: {green}/{red}\n"
            msg += f"Top asing beli: {', '.join(s for s, c in top_fb_stocks)}\n"
            msg += f"\n💡 /analyze BBCA — analisa detail saham"

            await update.message.reply_text(msg, parse_mode="Markdown")

        except Exception as e:
            print(f"Error in marketreport: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text("❌ Error: /marketreport tidak tersedia saat ini")
