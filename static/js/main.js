/**
 * EtuPlan — main.js
 * Calcul automatique de l'heure de fin + alertes dynamiques
 */

document.addEventListener('DOMContentLoaded', function () {
  const heureDebutInput = document.getElementById('heureDebut');
  const dureeInput      = document.getElementById('dureeMin');
  const heureFinDisplay = document.getElementById('heureFin');

  function calcHeureFin() {
    if (!heureDebutInput || !dureeInput || !heureFinDisplay) return;
    const debut  = heureDebutInput.value;
    const duree  = parseInt(dureeInput.value, 10);
    if (!debut || isNaN(duree)) { heureFinDisplay.textContent = '—'; return; }
    const [h, m] = debut.split(':').map(Number);
    const totalMin = h * 60 + m + duree;
    const hFin = String(Math.floor(totalMin / 60)).padStart(2, '0');
    const mFin = String(totalMin % 60).padStart(2, '0');
    heureFinDisplay.textContent = `${hFin}:${mFin}`;
  }

  if (heureDebutInput) heureDebutInput.addEventListener('input', calcHeureFin);
  if (dureeInput)      dureeInput.addEventListener('input', calcHeureFin);
  calcHeureFin(); // calcul initial si valeurs pré-remplies

  // Auto-dismiss des alertes flash après 6 secondes
  document.querySelectorAll('.alert.alert-danger, .alert.alert-warning').forEach(function (el) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 8000);
  });

  // Pagination "Voir plus" pour les tableaux
  document.querySelectorAll('table.table-paginate').forEach(function(table) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    let limit = 15;
    const wrapper = document.createElement('div');
    wrapper.className = 'text-center mt-3 mb-2 d-print-none';
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm btn-outline-primary rounded-pill px-4 fw-semibold';
    btn.innerHTML = 'Voir plus <i class="bi bi-chevron-down ms-1"></i>';
    wrapper.appendChild(btn);
    
    const tableResp = table.closest('.table-responsive');
    if (tableResp) {
      tableResp.parentNode.insertBefore(wrapper, tableResp.nextSibling);
    } else {
      table.parentNode.insertBefore(wrapper, table.nextSibling);
    }
    
    function updateVisibility() {
      const rows = Array.from(tbody.querySelectorAll('tr:not(.no-paginate)'));
      let visibleCount = 0;
      let totalMatch = 0;
      
      rows.forEach(r => {
        if (r.dataset.filtered === 'true') {
          r.style.display = 'none';
          return;
        }
        totalMatch++;
        if (visibleCount < limit) {
          r.style.display = '';
          visibleCount++;
        } else {
          r.style.display = 'none';
        }
      });
      
      wrapper.style.display = (totalMatch > limit) ? 'block' : 'none';
    }
    
    btn.addEventListener('click', function() {
      limit += 15;
      updateVisibility();
    });
    
    updateVisibility();
    table.updatePagination = updateVisibility;
  });
});
