"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const WHATSAPP = "https://wa.me/573187993643?text=Hola%2C%20quiero%20m%C3%A1s%20informaci%C3%B3n%20sobre%20SoluMed%20para%20mi%20drogue%C3%ADa";

const PLANES = [
  {
    id: "mensual",
    nombre: "Mensual",
    precio: "30.000",
    periodo: "/ mes",
    desc: "Ideal para empezar o evaluar el sistema sin compromiso.",
    color: "#2563eb",
    colorLight: "#eff6ff",
    badge: null,
    usuarios: "Hasta 3 usuarios",
    features: [
      "Recepción técnica con OCR",
      "Validación INVIMA en tiempo real",
      "Generación de actas en PDF",
      "Historial de recepciones",
      "Exportación a Excel",
      "Soporte por WhatsApp",
    ],
  },
  {
    id: "semestral",
    nombre: "Semestral",
    precio: "160.000",
    periodo: "/ 6 meses",
    desc: "El plan más elegido. Ahorra $20.000 vs pago mensual.",
    color: "#0f766e",
    colorLight: "#f0fdfa",
    badge: "MÁS POPULAR",
    usuarios: "Hasta 5 usuarios",
    features: [
      "Todo lo del plan Mensual",
      "Hasta 5 usuarios por droguería",
      "Reportes estadísticos avanzados",
      "Búsqueda en cosméticos INVIMA",
      "Historial RS vencidos (auditoría)",
      "Soporte prioritario",
    ],
  },
  {
    id: "anual",
    nombre: "Anual",
    precio: "300.000",
    periodo: "/ año",
    desc: "La mejor inversión. Ahorra $60.000 vs el plan mensual.",
    color: "#7c3aed",
    colorLight: "#faf5ff",
    badge: "MEJOR VALOR",
    usuarios: "Hasta 10 usuarios",
    features: [
      "Todo lo del plan Semestral",
      "Hasta 10 usuarios por droguería",
      "Acceso anticipado a nuevas funciones",
      "Capacitación virtual incluida",
      "Respaldo de datos garantizado",
      "Soporte dedicado 24/7",
    ],
  },
];

const PASOS = [
  {
    n: "01",
    titulo: "Sube la factura",
    desc: "Carga el PDF o imagen de tu factura del proveedor. El sistema la procesa automáticamente con OCR.",
    icon: "📄",
  },
  {
    n: "02",
    titulo: "Validación INVIMA",
    desc: "Cada producto se cruza en tiempo real con el catálogo oficial del INVIMA en datos.gov.co.",
    icon: "🔍",
  },
  {
    n: "03",
    titulo: "Evaluación técnica",
    desc: "El regente revisa, califica defectos y toma la decisión de aceptar o rechazar cada ítem.",
    icon: "✅",
  },
  {
    n: "04",
    titulo: "Acta y Excel",
    desc: "Se genera automáticamente el acta en PDF y el reporte Excel listo para presentar al INVIMA.",
    icon: "📊",
  },
];

export default function InfoPage() {
  const router = useRouter();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setTimeout(() => setVisible(true), 100);
  }, []);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body { font-family: 'Sora', sans-serif; background: #f8fafc; color: #0f172a; }

        .page { min-height: 100vh; overflow-x: hidden; }

        /* NAV */
        .nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          padding: 0 5vw;
          height: 64px;
          display: flex; align-items: center; justify-content: space-between;
          background: rgba(255,255,255,0.92);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid #e2e8f0;
        }
        .nav-logo {
          font-size: 22px; font-weight: 800; color: #1e3a5f;
          letter-spacing: -0.5px;
        }
        .nav-logo span { color: #2563eb; }
        .nav-links { display: flex; gap: 8px; align-items: center; }
        .nav-btn {
          padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
          font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 600;
          transition: all .2s;
        }
        .nav-btn-ghost { background: transparent; color: #475569; }
        .nav-btn-ghost:hover { background: #f1f5f9; color: #1e3a5f; }
        .nav-btn-primary {
          background: #2563eb; color: white;
          box-shadow: 0 2px 8px rgba(37,99,235,.3);
        }
        .nav-btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }

        /* HERO */
        .hero {
          padding-top: 64px;
          min-height: 100vh;
          display: flex; align-items: center;
          position: relative;
          overflow: hidden;
          background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #164e63 100%);
        }
        .hero-bg-grid {
          position: absolute; inset: 0;
          background-image: 
            linear-gradient(rgba(37,99,235,.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,99,235,.08) 1px, transparent 1px);
          background-size: 60px 60px;
        }
        .hero-bg-glow {
          position: absolute;
          width: 600px; height: 600px;
          background: radial-gradient(circle, rgba(37,99,235,.25) 0%, transparent 70%);
          top: 50%; left: 60%; transform: translate(-50%, -50%);
          pointer-events: none;
        }
        .hero-content {
          position: relative; z-index: 2;
          padding: 80px 5vw;
          max-width: 1200px; margin: 0 auto;
          display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center;
        }
        .hero-badge {
          display: inline-flex; align-items: center; gap: 8px;
          background: rgba(37,99,235,.2); border: 1px solid rgba(37,99,235,.4);
          padding: 6px 14px; border-radius: 20px;
          font-size: 12px; font-weight: 600; color: #93c5fd;
          letter-spacing: .08em; text-transform: uppercase;
          margin-bottom: 24px;
        }
        .hero-badge-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: #3b82f6;
          animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: .5; transform: scale(1.5); }
        }
        .hero h1 {
          font-size: clamp(36px, 4vw, 56px);
          font-weight: 800; line-height: 1.1;
          color: white; margin-bottom: 24px;
          letter-spacing: -1px;
        }
        .hero h1 em {
          font-style: normal;
          background: linear-gradient(90deg, #60a5fa, #34d399);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .hero-sub {
          font-size: 17px; line-height: 1.7;
          color: #94a3b8; margin-bottom: 40px;
          font-weight: 300;
        }
        .hero-btns { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn-hero-primary {
          padding: 14px 28px; border-radius: 10px; border: none; cursor: pointer;
          background: #2563eb; color: white;
          font-family: 'Sora', sans-serif; font-size: 15px; font-weight: 700;
          display: flex; align-items: center; gap: 8px;
          box-shadow: 0 4px 20px rgba(37,99,235,.4);
          transition: all .2s;
        }
        .btn-hero-primary:hover { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 8px 30px rgba(37,99,235,.5); }
        .btn-hero-wa {
          padding: 14px 28px; border-radius: 10px; border: none; cursor: pointer;
          background: rgba(255,255,255,.1); color: white; border: 1px solid rgba(255,255,255,.2);
          font-family: 'Sora', sans-serif; font-size: 15px; font-weight: 600;
          display: flex; align-items: center; gap: 8px;
          transition: all .2s; backdrop-filter: blur(8px);
        }
        .btn-hero-wa:hover { background: rgba(255,255,255,.18); transform: translateY(-2px); }

        /* MOCKUP */
        .hero-mockup {
          background: rgba(255,255,255,.05);
          border: 1px solid rgba(255,255,255,.1);
          border-radius: 20px; padding: 24px;
          backdrop-filter: blur(10px);
        }
        .mock-bar {
          display: flex; gap: 6px; margin-bottom: 16px;
        }
        .mock-dot { width: 10px; height: 10px; border-radius: 50%; }
        .mock-screen {
          background: #0f172a; border-radius: 12px;
          padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 12px;
        }
        .mock-line { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.05); }
        .mock-line:last-child { border-bottom: none; }
        .tag {
          padding: 2px 8px; border-radius: 4px;
          font-size: 10px; font-weight: 700; white-space: nowrap;
        }
        .tag-green { background: rgba(22,163,74,.2); color: #4ade80; }
        .tag-red { background: rgba(220,38,38,.2); color: #f87171; }
        .tag-blue { background: rgba(37,99,235,.2); color: #60a5fa; }

        /* STATS */
        .stats-section {
          background: white; border-bottom: 1px solid #e2e8f0;
          padding: 48px 5vw;
        }
        .stats-grid {
          max-width: 1200px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 32px;
        }
        .stat-item { text-align: center; }
        .stat-num {
          font-size: 40px; font-weight: 800; color: #1e3a5f;
          letter-spacing: -2px; line-height: 1;
          margin-bottom: 8px;
          font-family: 'JetBrains Mono', monospace;
        }
        .stat-num span { color: #2563eb; }
        .stat-lbl { font-size: 14px; color: #64748b; font-weight: 500; }

        /* SECTION COMÚN */
        .section { padding: 96px 5vw; }
        .section-inner { max-width: 1200px; margin: 0 auto; }
        .section-tag {
          font-size: 11px; font-weight: 700; letter-spacing: .12em;
          text-transform: uppercase; color: #2563eb;
          margin-bottom: 12px;
          font-family: 'JetBrains Mono', monospace;
        }
        .section-title {
          font-size: clamp(28px, 3vw, 42px); font-weight: 800;
          color: #0f172a; letter-spacing: -1px; line-height: 1.2;
          margin-bottom: 16px;
        }
        .section-sub {
          font-size: 17px; color: #64748b; line-height: 1.7; font-weight: 300;
          max-width: 560px;
        }

        /* PASOS */
        .pasos-grid {
          display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px;
          margin-top: 64px;
        }
        .paso-card {
          background: white; border-radius: 16px;
          padding: 32px 24px;
          border: 1px solid #e2e8f0;
          position: relative;
          transition: all .3s;
        }
        .paso-card:hover {
          transform: translateY(-6px);
          box-shadow: 0 20px 60px rgba(0,0,0,.08);
          border-color: #bfdbfe;
        }
        .paso-n {
          font-family: 'JetBrains Mono', monospace;
          font-size: 48px; font-weight: 700;
          color: #eff6ff; line-height: 1;
          margin-bottom: 8px;
          position: absolute; top: 20px; right: 20px;
        }
        .paso-icon { font-size: 36px; margin-bottom: 20px; }
        .paso-titulo { font-size: 17px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }
        .paso-desc { font-size: 14px; color: #64748b; line-height: 1.6; font-weight: 300; }
        .paso-connector {
          position: absolute; top: 50%; right: -24px;
          color: #cbd5e1; font-size: 20px;
          display: flex; align-items: center;
        }

        /* PLANES */
        .planes-section { background: #f8fafc; padding: 96px 5vw; }
        .planes-grid {
          display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;
          margin-top: 64px;
          max-width: 1200px; margin-left: auto; margin-right: auto;
        }
        .plan-card {
          background: white; border-radius: 20px;
          border: 2px solid #e2e8f0;
          overflow: hidden; position: relative;
          transition: all .3s;
          display: flex; flex-direction: column;
        }
        .plan-card:hover {
          transform: translateY(-8px);
          box-shadow: 0 30px 80px rgba(0,0,0,.1);
        }
        .plan-card.featured {
          border-width: 2px;
          transform: scale(1.04);
        }
        .plan-card.featured:hover { transform: scale(1.04) translateY(-8px); }
        .plan-badge {
          position: absolute; top: 16px; right: 16px;
          padding: 4px 10px; border-radius: 20px;
          font-size: 10px; font-weight: 800; letter-spacing: .08em;
          color: white;
        }
        .plan-header { padding: 36px 32px 28px; }
        .plan-nombre { font-size: 13px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 16px; font-family: 'JetBrains Mono', monospace; }
        .plan-precio-wrap { display: flex; align-items: baseline; gap: 6px; margin-bottom: 8px; }
        .plan-precio { font-size: 44px; font-weight: 800; letter-spacing: -2px; line-height: 1; }
        .plan-moneda { font-size: 20px; font-weight: 600; margin-top: 8px; }
        .plan-periodo { font-size: 14px; color: #94a3b8; font-weight: 400; }
        .plan-desc { font-size: 14px; color: #64748b; line-height: 1.6; margin-top: 12px; font-weight: 300; }
        .plan-body { padding: 0 32px 36px; flex: 1; display: flex; flex-direction: column; }
        .plan-usuarios {
          display: flex; align-items: center; gap: 8px;
          padding: 10px 14px; border-radius: 8px;
          font-size: 13px; font-weight: 600;
          margin-bottom: 24px;
        }
        .plan-features { list-style: none; flex: 1; margin-bottom: 32px; }
        .plan-feature {
          display: flex; align-items: flex-start; gap: 10px;
          padding: 9px 0; font-size: 14px; color: #374151;
          border-bottom: 1px solid #f1f5f9; font-weight: 400;
        }
        .plan-feature:last-child { border-bottom: none; }
        .feature-check { font-size: 14px; flex-shrink: 0; margin-top: 1px; }
        .plan-cta {
          width: 100%; padding: 14px; border-radius: 12px;
          border: none; cursor: pointer;
          font-family: 'Sora', sans-serif; font-size: 15px; font-weight: 700;
          transition: all .2s; display: flex; align-items: center;
          justify-content: center; gap: 8px;
        }

        /* POR QUÉ */
        .porque-grid {
          display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;
          margin-top: 64px;
        }
        .porque-card {
          padding: 32px; border-radius: 16px;
          background: white; border: 1px solid #e2e8f0;
          transition: all .3s;
        }
        .porque-card:hover { transform: translateY(-4px); box-shadow: 0 16px 48px rgba(0,0,0,.06); }
        .porque-icon {
          width: 52px; height: 52px; border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          font-size: 24px; margin-bottom: 20px;
        }
        .porque-titulo { font-size: 17px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }
        .porque-desc { font-size: 14px; color: #64748b; line-height: 1.65; font-weight: 300; }

        /* CTA FINAL */
        .cta-section {
          background: linear-gradient(135deg, #0f172a, #1e3a5f);
          padding: 96px 5vw; text-align: center;
          position: relative; overflow: hidden;
        }
        .cta-glow {
          position: absolute; width: 500px; height: 500px;
          background: radial-gradient(circle, rgba(37,99,235,.2) 0%, transparent 70%);
          top: 50%; left: 50%; transform: translate(-50%,-50%);
          pointer-events: none;
        }
        .cta-content { position: relative; z-index: 2; }
        .cta-title {
          font-size: clamp(28px, 3vw, 48px); font-weight: 800;
          color: white; letter-spacing: -1px; margin-bottom: 16px;
        }
        .cta-sub { font-size: 17px; color: #94a3b8; margin-bottom: 40px; font-weight: 300; }
        .cta-btns { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }

        /* FOOTER */
        .footer {
          background: #0f172a; padding: 40px 5vw;
          text-align: center; border-top: 1px solid rgba(255,255,255,.05);
        }
        .footer-logo { font-size: 20px; font-weight: 800; color: white; margin-bottom: 8px; }
        .footer-logo span { color: #3b82f6; }
        .footer-copy { font-size: 13px; color: #475569; }

        /* ANIM */
        .fade-up {
          opacity: 0; transform: translateY(30px);
          transition: opacity .7s ease, transform .7s ease;
        }
        .fade-up.in { opacity: 1; transform: translateY(0); }

        /* RESPONSIVE */
        @media (max-width: 768px) {
          .hero-content { grid-template-columns: 1fr; gap: 40px; padding: 60px 5vw; }
          .hero-mockup { display: none; }
          .stats-grid { grid-template-columns: repeat(2, 1fr); }
          .pasos-grid { grid-template-columns: 1fr 1fr; }
          .planes-grid { grid-template-columns: 1fr; }
          .plan-card.featured { transform: none; }
          .porque-grid { grid-template-columns: 1fr 1fr; }
          .planes-section { padding: 64px 5vw; }
          .section { padding: 64px 0; }
          .cta-section { padding: 64px 5vw; }
          .section-title { font-size: clamp(24px, 5vw, 36px) !important; }
        }
        @media (max-width: 520px) {
          .nav-btn-ghost { display: none; }
          .nav-btn-primary { padding: 8px 14px; font-size: 13px; }
          .hero h1 { font-size: clamp(28px, 8vw, 40px); }
          .hero-sub { font-size: 15px; }
          .btn-hero-primary, .btn-hero-wa { width: 100%; justify-content: center; padding: 13px 20px; font-size: 14px; }
          .hero-btns { flex-direction: column; }
          .pasos-grid { grid-template-columns: 1fr; }
          .porque-grid { grid-template-columns: 1fr; }
          .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
          .stat-num { font-size: 36px !important; }
          .plan-header { padding: 24px 20px 20px; }
          .plan-body { padding: 0 20px 24px; }
          .cta-btns { flex-direction: column; align-items: center; }
          .cta-btns button { width: 100%; max-width: 360px; }
          .paso-connector { display: none !important; }
        }
      `}</style>

      <div className="page">

        {/* NAV */}
        <nav className="nav">
          <div className="nav-logo">Solu<span>Med</span></div>
          <div className="nav-links">
            <button className="nav-btn nav-btn-ghost" onClick={() => document.getElementById('planes')?.scrollIntoView({behavior:'smooth'})}>
              Planes
            </button>
            <button className="nav-btn nav-btn-ghost" onClick={() => window.open(WHATSAPP, '_blank')}>
              Contacto
            </button>
            <button className="nav-btn nav-btn-primary" onClick={() => router.push('/login')}>
              Iniciar sesión
            </button>
          </div>
        </nav>

        {/* HERO */}
        <section className="hero">
          <div className="hero-bg-grid" />
          <div className="hero-bg-glow" />
          <div className="hero-content">
            <div className={`fade-up ${visible ? 'in' : ''}`}>
              <div className="hero-badge">
                <div className="hero-badge-dot" />
                Software para droguerías colombianas
              </div>
              <h1>
                Recepción técnica<br />
                <em>sin papel, sin errores,</em><br />
                con el INVIMA.
              </h1>
              <p className="hero-sub">
                SoluMed automatiza la recepción técnica de medicamentos: extrae los productos de tu factura, los valida contra el catálogo oficial del INVIMA y genera el acta lista para firmar — todo en minutos.
              </p>
              <div className="hero-btns">
                <button className="btn-hero-primary" onClick={() => document.getElementById('planes')?.scrollIntoView({behavior:'smooth'})}>
                  Ver planes y precios →
                </button>
                <button className="btn-hero-wa" onClick={() => window.open(WHATSAPP, '_blank')}>
                  <span>💬</span> Hablar por WhatsApp
                </button>
              </div>
            </div>

            {/* MOCKUP */}
            <div className={`hero-mockup fade-up in`} style={{transitionDelay:'.2s'}}>
              <div className="mock-bar">
                <div className="mock-dot" style={{background:'#ef4444'}} />
                <div className="mock-dot" style={{background:'#f59e0b'}} />
                <div className="mock-dot" style={{background:'#22c55e'}} />
                <span style={{marginLeft:8, fontSize:11, color:'#64748b', fontFamily:'monospace'}}>Recepción técnica — FAC-2024-001</span>
              </div>
              <div className="mock-screen">
                {[
                  {nom:'CIPROFLOXACINO 500MG',invima:'Vigente',dec:'Acepta'},
                  {nom:'METFORMINA 850MG',invima:'Vigente',dec:'Acepta'},
                  {nom:'AMOXICILINA 500MG',invima:'Vigente',dec:'Acepta'},
                  {nom:'LOSARTAN 50MG',invima:'Vencido',dec:'Rechaza'},
                  {nom:'IBUPROFENO 400MG',invima:'Vigente',dec:'Acepta'},
                ].map((p,i) => (
                  <div className="mock-line" key={i}>
                    <span style={{color:'#94a3b8', minWidth:20}}>{i+1}</span>
                    <span style={{color:'#e2e8f0', flex:1, fontSize:11}}>{p.nom}</span>
                    <span className={`tag ${p.invima==='Vigente'?'tag-green':'tag-red'}`}>{p.invima}</span>
                    <span className={`tag ${p.dec==='Acepta'?'tag-green':'tag-red'}`}>{p.dec}</span>
                  </div>
                ))}
                <div style={{marginTop:12, padding:'8px 0', borderTop:'1px solid rgba(255,255,255,.08)', display:'flex', justifyContent:'space-between'}}>
                  <span style={{color:'#22c55e', fontSize:11, fontFamily:'monospace'}}>✓ 4 aceptados</span>
                  <span style={{color:'#f87171', fontSize:11, fontFamily:'monospace'}}>✗ 1 rechazado</span>
                  <span style={{color:'#3b82f6', fontSize:11, fontFamily:'monospace'}}>📄 PDF generado</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STATS */}
        <div className="stats-section">
          <div className="stats-grid">
            {[
              {num:'63', suf:'+', lbl:'Datasets INVIMA integrados'},
              {num:'100', suf:'%', lbl:'Validación en tiempo real'},
              {num:'< 3', suf:'min', lbl:'Por factura procesada'},
              {num:'0', suf:'', lbl:'Papel necesario'},
            ].map((s,i) => (
              <div className="stat-item" key={i}>
                <div className="stat-num">{s.num}<span>{s.suf}</span></div>
                <div className="stat-lbl">{s.lbl}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CÓMO FUNCIONA */}
        <section className="section">
          <div className="section-inner">
            <div className="section-tag">// cómo funciona</div>
            <h2 className="section-title">De la factura al acta<br />en 4 pasos</h2>
            <p className="section-sub">Sin instalaciones complejas. Sin capacitación extensa. Desde el primer día.</p>
            <div className="pasos-grid">
              {PASOS.map((p, i) => (
                <div className="paso-card" key={i}>
                  <div className="paso-n">{p.n}</div>
                  <div className="paso-icon">{p.icon}</div>
                  <div className="paso-titulo">{p.titulo}</div>
                  <div className="paso-desc">{p.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PLANES */}
        <section className="planes-section" id="planes">
          <div className="section-inner">
            <div className="section-tag" style={{textAlign:'center'}}>// planes y precios</div>
            <h2 className="section-title" style={{textAlign:'center'}}>Elige tu plan</h2>
            <p className="section-sub" style={{textAlign:'center', margin:'0 auto 0'}}>
              Sin contratos. Sin permanencia. Cancela cuando quieras.<br/>
              Todos los planes incluyen soporte por WhatsApp.
            </p>
            <div className="planes-grid">
              {PLANES.map((plan) => (
                <div
                  key={plan.id}
                  className={`plan-card ${plan.badge === 'MÁS POPULAR' ? 'featured' : ''}`}
                  style={{ borderColor: plan.badge ? plan.color : '#e2e8f0' }}
                >
                  {plan.badge && (
                    <div className="plan-badge" style={{background: plan.color}}>
                      {plan.badge}
                    </div>
                  )}
                  <div className="plan-header" style={{borderBottom:`3px solid ${plan.color}`}}>
                    <div className="plan-nombre" style={{color: plan.color}}>{plan.nombre}</div>
                    <div className="plan-precio-wrap">
                      <span className="plan-moneda" style={{color: plan.color}}>$</span>
                      <span className="plan-precio" style={{color: '#0f172a'}}>{plan.precio}</span>
                    </div>
                    <div className="plan-periodo">{plan.periodo} · COP</div>
                    <p className="plan-desc">{plan.desc}</p>
                  </div>
                  <div className="plan-body">
                    <div className="plan-usuarios" style={{background: plan.colorLight, color: plan.color}}>
                      <span>👥</span> {plan.usuarios}
                    </div>
                    <ul className="plan-features">
                      {plan.features.map((f, i) => (
                        <li className="plan-feature" key={i}>
                          <span className="feature-check" style={{color: plan.color}}>✓</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                    <button
                      className="plan-cta"
                      style={{
                        background: plan.color,
                        color: 'white',
                        boxShadow: `0 4px 16px ${plan.color}40`
                      }}
                      onClick={() => window.open(
                        `${WHATSAPP}&text=Hola%2C%20quiero%20contratar%20el%20plan%20${encodeURIComponent(plan.nombre)}%20de%20SoluMed`,
                        '_blank'
                      )}
                    >
                      <span>💬</span> Contratar por WhatsApp
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <p style={{textAlign:'center', marginTop:32, fontSize:13, color:'#94a3b8'}}>
              * Precios en pesos colombianos (COP) · IVA no incluido · El plan inicia tras confirmación de pago
            </p>
          </div>
        </section>

        {/* POR QUÉ SOLUMED */}
        <section className="section" style={{background:'white'}}>
          <div className="section-inner">
            <div className="section-tag">// por qué solumed</div>
            <h2 className="section-title">Hecho para droguerías<br />colombianas</h2>
            <div className="porque-grid" style={{marginTop:48}}>
              {[
                {icon:'🏛️', color:'#eff6ff', titulo:'API INVIMA oficial', desc:'Consultamos directamente datos.gov.co con los registros sanitarios vigentes del INVIMA. Sin datos desactualizados ni bases propias.'},
                {icon:'📊', color:'#f0fdf4', titulo:'Excel para auditorías', desc:'Genera automáticamente el libro Excel con una hoja por mes, listo para presentar ante el INVIMA en una visita de control.'},
                {icon:'🔒', color:'#faf5ff', titulo:'Multi-droguería seguro', desc:'Cada droguería ve únicamente sus propios datos. Sistema de roles: superadmin, administrador y regente de farmacia.'},
                {icon:'📄', color:'#fff7ed', titulo:'Actas en PDF', desc:'Genera el acta técnica de recepción con espacios de firma, resumen de aceptados/rechazados y código de factura.'},
                {icon:'⚡', color:'#fffbeb', titulo:'OCR inteligente', desc:'Extrae automáticamente los productos de la factura (PDF o imagen). Sin digitar nada manualmente.'},
                {icon:'🇨🇴', color:'#f0fdf4', titulo:'Soporte colombiano', desc:'Atención directa por WhatsApp con el desarrollador. Respuesta rápida, sin bots, sin tickets internacionales.'},
              ].map((c,i) => (
                <div className="porque-card" key={i}>
                  <div className="porque-icon" style={{background: c.color}}>{c.icon}</div>
                  <div className="porque-titulo">{c.titulo}</div>
                  <div className="porque-desc">{c.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA FINAL */}
        <section className="cta-section">
          <div className="cta-glow" />
          <div className="cta-content">
            <h2 className="cta-title">¿Listo para modernizar<br />tu droguería?</h2>
            <p className="cta-sub">Escríbenos ahora y te ayudamos a crear tu cuenta en minutos.</p>
            <div className="cta-btns">
              <button
                style={{
                  padding:'16px 32px', borderRadius:12, border:'none', cursor:'pointer',
                  background:'#25D366', color:'white',
                  fontFamily:'Sora, sans-serif', fontSize:16, fontWeight:700,
                  display:'flex', alignItems:'center', gap:10,
                  boxShadow:'0 4px 24px rgba(37,211,102,.4)',
                  transition:'all .2s'
                }}
                onMouseEnter={e => (e.currentTarget.style.transform='translateY(-2px)')}
                onMouseLeave={e => (e.currentTarget.style.transform='none')}
                onClick={() => window.open(WHATSAPP, '_blank')}
              >
                <span style={{fontSize:20}}>💬</span>
                Escribir por WhatsApp
              </button>
              <button
                style={{
                  padding:'16px 32px', borderRadius:12, cursor:'pointer',
                  background:'transparent', color:'white',
                  border:'1px solid rgba(255,255,255,.3)',
                  fontFamily:'Sora, sans-serif', fontSize:16, fontWeight:600,
                  transition:'all .2s'
                }}
                onMouseEnter={e => (e.currentTarget.style.background='rgba(255,255,255,.1)')}
                onMouseLeave={e => (e.currentTarget.style.background='transparent')}
                onClick={() => router.push('/login')}
              >
                Ya tengo cuenta →
              </button>
            </div>
            <div style={{marginTop:40, display:'flex', justifyContent:'center', gap:32, flexWrap:'wrap'}}>
              {['Sin permanencia','Soporte incluido','Datos protegidos','Pago por WhatsApp'].map(t => (
                <span key={t} style={{fontSize:13, color:'#64748b', display:'flex', alignItems:'center', gap:6}}>
                  <span style={{color:'#22c55e'}}>✓</span> {t}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="footer">
          <div className="footer-logo">Solu<span>Med</span></div>
          <p className="footer-copy" style={{marginTop:8}}>
            Software de recepción técnica para droguerías colombianas · +57 318 799 3643
          </p>
          <p className="footer-copy" style={{marginTop:4}}>
            © {new Date().getFullYear()} SoluMed · Todos los derechos reservados
          </p>
        </footer>

      </div>
    </>
  );
}