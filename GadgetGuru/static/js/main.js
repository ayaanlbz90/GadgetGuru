// ---------------------------------------------------------------
// GadgetGuru front-end behaviour
// ---------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {

  // --- Mobile menu toggle (distinct full-panel slide-in) ---
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  const mobileMenu = document.getElementById('mobileMenu');
  const mobileOverlay = document.getElementById('mobileOverlay');
  const mobileMenuClose = document.getElementById('mobileMenuClose');

  function openMobileMenu() {
    mobileMenu.classList.add('open');
    mobileOverlay.classList.add('open');
    hamburgerBtn.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeMobileMenu() {
    mobileMenu.classList.remove('open');
    mobileOverlay.classList.remove('open');
    hamburgerBtn.classList.remove('open');
    document.body.style.overflow = '';
  }
  if (hamburgerBtn) {
    hamburgerBtn.addEventListener('click', function () {
      mobileMenu.classList.contains('open') ? closeMobileMenu() : openMobileMenu();
    });
  }
  if (mobileMenuClose) mobileMenuClose.addEventListener('click', closeMobileMenu);
  if (mobileOverlay) mobileOverlay.addEventListener('click', closeMobileMenu);

  // --- Flash message auto-dismiss ---
  const flashWrap = document.getElementById('flashWrap');
  if (flashWrap) {
    setTimeout(function () {
      flashWrap.style.transition = 'opacity 0.4s ease';
      flashWrap.style.opacity = '0';
      setTimeout(() => flashWrap.remove(), 400);
    }, 3500);
  }

  // --- Quantity stepper controls (product detail / cart) ---
  document.querySelectorAll('[data-qty-control]').forEach(function (control) {
    const input = control.querySelector('input[type="number"]');
    const minus = control.querySelector('[data-qty-minus]');
    const plus = control.querySelector('[data-qty-plus]');
    if (minus) minus.addEventListener('click', function () {
      input.value = Math.max(1, parseInt(input.value || '1', 10) - 1);
    });
    if (plus) plus.addEventListener('click', function () {
      input.value = parseInt(input.value || '1', 10) + 1;
    });
  });

  // --- Category filter chips (client-side, index page) ---
  const chips = document.querySelectorAll('[data-category-chip]');
  const cards = document.querySelectorAll('[data-product-card]');
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const cat = chip.dataset.categoryChip;
      cards.forEach(function (card) {
        if (cat === 'all' || card.dataset.category === cat) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // --- Payment method selection highlight ---
  document.querySelectorAll('.pay-option input').forEach(function (radio) {
    radio.addEventListener('change', function () {
      document.querySelectorAll('.pay-option').forEach(el => el.classList.remove('selected'));
      radio.closest('.pay-option').classList.add('selected');
      const qrSection = document.getElementById('qrSection');
      if (qrSection) {
        qrSection.style.display = radio.value === 'UPI' ? 'block' : 'none';
      }
    });
  });

  // --- Copy UPI ID button ---
  const copyBtn = document.getElementById('copyUpiBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      const upiId = copyBtn.dataset.upi;
      navigator.clipboard.writeText(upiId).then(function () {
        const original = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = original; }, 1500);
      });
    });
  }

  // --- File input preview (admin add/edit product) ---
  const fileInput = document.getElementById('productImageInput');
  const fileDrop = document.getElementById('fileDrop');
  if (fileInput && fileDrop) {
    fileInput.addEventListener('change', function () {
      if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
          fileDrop.innerHTML = '<img src="' + e.target.result + '" alt="Preview"><p>' + fileInput.files[0].name + '</p>';
        };
        reader.readAsDataURL(fileInput.files[0]);
      }
    });
  }
});
