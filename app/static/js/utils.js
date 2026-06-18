// ─── Utility / Format Helpers ───
function formatRp(val) {
  if (val >= 1e12) return 'Rp' + (val/1e12).toFixed(2) + 'T';
  if (val >= 1e9) return 'Rp' + (val/1e9).toFixed(1) + 'M';
  if (val >= 1e6) return 'Rp' + (val/1e6).toFixed(1) + 'Jt';
  return 'Rp' + val.toLocaleString('id');
}
function formatVolume(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
  return v.toString();
}
function formatPrice(v) {
  return 'Rp ' + Math.round(v).toLocaleString('id-ID');
}
function fetchWithTimeout(url, timeoutMs) {
  timeoutMs = timeoutMs || 8000;
  var controller = new AbortController();
  var timer = setTimeout(function() { controller.abort(); }, timeoutMs);
  return fetch(url, { signal: controller.signal })
    .then(function(r) { clearTimeout(timer); return r.json(); })
    .catch(function(e) { clearTimeout(timer); return null; });
}
