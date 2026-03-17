/* FoodShare AI — Master Frontend Script
   Layers: Frontend (HTML/CSS/JS) ↔ Antigravity Platform (Flask API)
*/

// ── Scroll progress bar
window.addEventListener('scroll', () => {
  const d = document.documentElement;
  const p = (d.scrollTop / (d.scrollHeight - d.clientHeight)) * 100;
  const b = document.getElementById('progress-bar');
  if (b) b.style.width = p + '%';
});

// ── Parallax blobs
window.addEventListener('scroll', () => {
  const y = window.scrollY;
  const b1 = document.querySelector('.blob1');
  const b2 = document.querySelector('.blob2');
  if (b1) b1.style.transform = `translate(${y*.05}px,${y*.08}px) scale(1)`;
  if (b2) b2.style.transform = `translate(${-y*.04}px,${-y*.06}px) scale(1)`;
});

// ── Scroll reveal
const revealEls = document.querySelectorAll('.reveal');
if (revealEls.length) {
  const revealObs = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add('visible'), i * 80);
        revealObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  revealEls.forEach(el => revealObs.observe(el));
}

// ── Animated impact counters
const impactSection = document.getElementById('impact');
if (impactSection) {
  new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.querySelectorAll('.impact-num').forEach(n => {
          const text   = n.textContent;
          const num    = parseFloat(text.replace(/[^0-9.]/g, ''));
          const suffix = text.replace(/[0-9.]/g, '');
          if (!isNaN(num)) {
            let current = 0;
            const inc = num / 60;
            const t = setInterval(() => {
              current += inc;
              if (current >= num) { current = num; clearInterval(t); }
              n.textContent = Math.floor(current).toLocaleString() + suffix;
            }, 20);
          }
        });
      }
    });
  }, { threshold: 0.3 }).observe(impactSection);
}

// ── Food tag toggle (default behavior, template may override)
document.querySelectorAll('.food-tag').forEach(tag => {
  if (!tag.dataset.bound) {
    tag.dataset.bound = '1';
    tag.addEventListener('click', () => tag.classList.toggle('active'));
  }
});

// ── Dashboard sidebar nav
document.querySelectorAll('.dash-nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.dash-nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
  });
});

// ── Dashboard filter
document.querySelectorAll('.dlf-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.dlf-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});


/* ══════════════════════════════════════════════════════
   DONATION FORM  →  Supabase Insert
   ══════════════════════════════════════════════════════ */
async function handleDonate(btn) {
  const get = id => document.getElementById(id)?.value?.trim() || '';
  const donor_name  = get('field-name');
  const donor_email = get('field-email');
  const phone       = get('field-phone');
  const pincode     = get('field-pincode');
  const quantity    = get('field-quantity');
  const serves      = parseInt(get('field-serves')) || 0;
  const prepared_at = get('field-prepared');
  const best_before = get('field-expiry');
  const address     = get('field-address');
  const food_types  = [...document.querySelectorAll('.food-tag.active')]
                        .map(t => t.textContent.replace(/^[^\w]+/, '').trim());

  if (!donor_name) { showToast('⚠️ Please enter your name.', 'warn'); return; }
  if (!address)    { showToast('⚠️ Please enter the pickup address.', 'warn'); return; }

  const orig = btn.textContent;
  btn.textContent = '⏳ Submitting Donation…';
  btn.disabled = true; btn.style.opacity = '.75';

  try {
    const res = await fetch('/api/donate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        donor_name,
        donor_email: donor_email || null,
        phone: phone || null,
        pincode: pincode || null,
        food_types,
        quantity,
        serves,
        prepared_at: prepared_at || null,
        best_before: best_before || null,
        address
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || 'Failed to submit donation');
    }

    btn.textContent = '✅ Submitted!';
    btn.style.background = 'linear-gradient(135deg,#27ae60,#1e8449)';
    btn.style.opacity = '1';

    showToast('🎉 Donation listed successfully!', 'success');

    // Optionally redirect after success
    setTimeout(() => window.location.href = '/dashboard', 2500);
  } catch (err) {
    btn.textContent = orig; btn.disabled = false; btn.style.opacity = '1';
    showToast('❌ ' + err.message, 'error');
  }
}

function showMatchCard(ngo, id, urgency) {
  document.getElementById('match-result')?.remove();
  const card = document.createElement('div');
  card.id = 'match-result';
  card.style.cssText = 'margin-top:1rem;padding:1.2rem;border-radius:14px;background:rgba(46,204,113,.1);border:1px solid rgba(46,204,113,.3)';
  const urgClass = urgency ? `<span style="font-size:.7rem;font-weight:700;padding:.2rem .6rem;border-radius:50px;background:rgba(${urgency.urgency_class==='HIGH'?'231,76,60':'243,156,18'},.15);color:${urgency.urgency_class==='HIGH'?'#e74c3c':'#f39c12'}">${urgency.urgency_class} urgency</span>` : '';
  card.innerHTML = `
    <div style="font-size:.72rem;color:var(--green);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem">🤖 AI Match #${escHtml(String(id))}</div>
    <div style="font-size:1rem;font-weight:600">${escHtml(ngo.name)} ${urgClass}</div>
    <div style="font-size:.82rem;color:var(--text-muted);margin-top:.25rem">📍 ${escHtml(ngo.area||'')} · ${ngo.distance_km} km away | Capacity: ${ngo.capacity} meals</div>
    <div style="font-size:.72rem;color:var(--text-muted);margin-top:.5rem">📧 Confirmation email sent · NGO notified</div>
  `;
  document.querySelector('.form-submit')?.insertAdjacentElement('afterend', card);
}


/* ══════════════════════════════════════════════════════
   DASHBOARD  →  Supabase Realtime
   ══════════════════════════════════════════════════════ */
async function loadDashboard() {
  if (!document.getElementById('metric-meals-today')) return;
  try {
    // 1. Get recent donations
    const { data: donations, error: donError } = await window.supabase
      .from('donations')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(20);
      
    if (donError) throw donError;
    
    // 2. Get impact stats
    const { data: impact, error: impError } = await window.supabase
      .from('impact')
      .select('*')
      .single();
      
    if (impError && impError.code !== 'PGRST116') throw impError; // Ignore 0 rows error

    // 3. Get active count (RPC or simple count)
    const { count: activeCount } = await window.supabase
      .from('donations')
      .select('*', { count: 'exact', head: true })
      .in('status', ['available', 'pending', 'matched']);

    setMetric('metric-meals-today', impact?.meals_rescued_total || 0); // Simplified, using total instead of today
    setMetric('metric-active',      activeCount || 0);
    setMetric('metric-resp-time',   (impact?.avg_response_time_min || 0) + 'm');
    setMetric('metric-co2',         impact?.co2_saved_kg || 0);
    renderDonationList(donations || []);
  } catch(e) { console.warn('[Dashboard] refresh failed', e); }
}

function setMetric(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(val);
}

function renderDonationList(donations) {
  const list = document.getElementById('dash-donation-list');
  if (!list) return;
  if (!donations.length) {
    list.innerHTML = '<div style="padding:1.5rem;text-align:center;color:var(--text-muted);font-size:.85rem">No donations yet</div>';
    return;
  }
  list.innerHTML = donations.map(d => {
    const ft   = (d.food_types||'').toLowerCase();
    const icon = ft.includes('bak')?'🎂':ft.includes('veg')?'🥗':'🍱';
    const badge = d.status==='matched'
      ? `<span class="dl-badge matched">Matched</span><button onclick="markComplete('${d.id}')" style="font-size:.62rem;padding:.25rem .6rem;border-radius:50px;border:1px solid rgba(46,204,113,.3);background:rgba(46,204,113,.08);color:var(--green);cursor:pointer;margin-left:.4rem">✓ Done</button>`
      : d.status==='completed'
      ? '<span class="dl-badge" style="background:rgba(255,255,255,.07);color:var(--text-muted)">Done</span>'
      : '<span class="dl-badge fresh">Pending</span>';
    return `<div class="dl-item" data-status="${d.status}">
      <div class="dl-avatar" style="background:rgba(46,204,113,.12)">${icon}</div>
      <div class="dl-info">
        <div class="dl-name">${escHtml(d.donor_name)} — ${escHtml(d.food_types||'Food')}</div>
        <div class="dl-meta">${escHtml(d.address||'')}${d.quantity?' · '+escHtml(d.quantity):''}</div>
      </div>${badge}</div>`;
  }).join('');
}

/* ══════════════════════════════════════════════════════
   STATUS UPDATE  →  Supabase Update
   ══════════════════════════════════════════════════════ */
async function markComplete(id) {
  try {
    const { error } = await window.supabase
      .from('donations')
      .update({ status: 'completed' })
      .eq('id', id);
      
    if (error) throw error;
    showToast('✅ Marked as completed', 'success'); 
    loadDashboard();
  } catch (err) { showToast('❌ Could not update status', 'error'); }
}

loadDashboard();

// Subscribe to Supabase Realtime changes for donations and impact
if (window.supabase && document.getElementById('metric-meals-today')) {
  window.supabase
    .channel('dashboard-changes')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'donations' }, payload => {
      console.log('Donation update received!', payload);
      loadDashboard();
    })
    .on('postgres_changes', { event: '*', schema: 'public', table: 'impact' }, payload => {
      console.log('Impact update received!', payload);
      loadDashboard();
    })
    .subscribe();
}


/* ══════════════════════════════════════════════════════
   UTILITIES
   ══════════════════════════════════════════════════════ */
function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function showToast(msg, type='success') {
  const bg  = {success:'rgba(46,204,113,.15)',warn:'rgba(243,156,18,.15)',error:'rgba(231,76,60,.15)'};
  const bdr = {success:'rgba(46,204,113,.4)', warn:'rgba(243,156,18,.4)', error:'rgba(231,76,60,.4)'};
  if (!document.getElementById('_tst')) {
    const s = document.createElement('style'); s.id='_tst';
    s.textContent='@keyframes tIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}@keyframes tOut{from{opacity:1}to{opacity:0;transform:translateY(20px)}}';
    document.head.appendChild(s);
  }
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:2rem;right:2rem;z-index:9000;background:${bg[type]};border:1px solid ${bdr[type]};backdrop-filter:blur(20px);color:var(--text);padding:.9rem 1.4rem;border-radius:14px;font-size:.875rem;font-weight:500;max-width:340px;animation:tIn .35s ease both;box-shadow:0 8px 32px rgba(0,0,0,.4)`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.animation='tOut .3s ease forwards'; setTimeout(()=>t.remove(),350); }, 4000);
}
