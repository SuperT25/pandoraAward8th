/**
 * Pandora E-Ticket System — Frontend JS
 * Sidebar toggle, QR scanner, auto-dismiss alerts
 */

// ── Sidebar toggle (mobile) ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const hamburger = document.getElementById('hamburger');
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebar-overlay');

  if (hamburger && sidebar) {
    hamburger.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('visible');
    });
  }

  if (overlay) {
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('visible');
    });
  }

  // Mark active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-nav a').forEach(link => {
    if (currentPath.startsWith(link.getAttribute('href'))) {
      link.classList.add('active');
    }
  });

  // Auto-dismiss alerts after 5 s
  document.querySelectorAll('.alert-auto-dismiss').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 500);
    }, 5000);
  });
});

// ── QR Scanner (using html5-qrcode CDN) ────────────────────────────────
function startQrScanner(containerId, onSuccess) {
  if (typeof Html5Qrcode === 'undefined') {
    alert('QR scanner library not loaded. Please check your internet connection.');
    return;
  }

  const html5QrCode = new Html5Qrcode(containerId);
  const config = {
    fps: 10,
    qrbox: { width: 250, height: 250 },
    aspectRatio: 1.0,
  };

  html5QrCode.start(
    { facingMode: 'environment' },  // rear camera
    config,
    function (decodedText) {
      html5QrCode.stop().catch(() => {});
      onSuccess(decodedText);
    },
    function (errorMsg) {
      // scan error — ignore, keep scanning
    }
  ).catch(function (err) {
    document.getElementById(containerId).innerHTML =
      '<p style="color:#ff8800;padding:1rem;">Camera access denied or unavailable.<br>' +
      'Please use manual ticket number entry.</p>';
  });
}

// ── QR Scan button on verify page ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  const scanBtn       = document.getElementById('btn-scan-qr');
  const scanContainer = document.getElementById('qr-scanner-container');
  const scanRegion    = document.getElementById('qr-reader');

  if (!scanBtn) return;

  let scanning = false;

  scanBtn.addEventListener('click', function () {
    if (scanning) return;
    scanning = true;
    scanContainer.style.display = 'block';
    scanBtn.disabled = true;
    scanBtn.textContent = 'Scanning…';

    startQrScanner('qr-reader', function (token) {
      // Redirect to QR verify URL
      const baseUrl = scanBtn.dataset.verifyBase || '/verify/qr/';
      window.location.href = baseUrl + encodeURIComponent(token) + '/';
    });
  });
});

// ── Confirm dangerous actions ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      const msg = el.dataset.confirm || 'Are you sure?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });
});
