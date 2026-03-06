(()=>{var a={};a.id=811,a.ids=[811],a.modules={261:a=>{"use strict";a.exports=require("next/dist/shared/lib/router/utils/app-paths")},3295:a=>{"use strict";a.exports=require("next/dist/server/app-render/after-task-async-storage.external.js")},10846:a=>{"use strict";a.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},19121:a=>{"use strict";a.exports=require("next/dist/server/app-render/action-async-storage.external.js")},26713:a=>{"use strict";a.exports=require("next/dist/shared/lib/router/utils/is-bot")},28354:a=>{"use strict";a.exports=require("util")},29294:a=>{"use strict";a.exports=require("next/dist/server/app-render/work-async-storage.external.js")},32515:(a,b,c)=>{Promise.resolve().then(c.bind(c,62602))},33873:a=>{"use strict";a.exports=require("path")},41025:a=>{"use strict";a.exports=require("next/dist/server/app-render/dynamic-access-async-storage.external.js")},42378:(a,b,c)=>{"use strict";var d=c(91330);c.o(d,"usePathname")&&c.d(b,{usePathname:function(){return d.usePathname}}),c.o(d,"useRouter")&&c.d(b,{useRouter:function(){return d.useRouter}})},43600:(a,b,c)=>{"use strict";c.r(b),c.d(b,{default:()=>j});var d=c(21124),e=c(38301),f=c(42378);let g="https://wa.me/573187993643?text=Hola%2C%20quiero%20m%C3%A1s%20informaci%C3%B3n%20sobre%20SoluMed%20para%20mi%20drogue%C3%ADa",h=[{id:"mensual",nombre:"Mensual",precio:"30.000",periodo:"/ mes",desc:"Ideal para empezar o evaluar el sistema sin compromiso.",color:"#2563eb",colorLight:"#eff6ff",badge:null,usuarios:"Hasta 3 usuarios",features:["Recepci\xf3n t\xe9cnica con OCR","Validaci\xf3n INVIMA en tiempo real","Generaci\xf3n de actas en PDF","Historial de recepciones","Exportaci\xf3n a Excel","Soporte por WhatsApp"]},{id:"semestral",nombre:"Semestral",precio:"160.000",periodo:"/ 6 meses",desc:"El plan m\xe1s elegido. Ahorra $20.000 vs pago mensual.",color:"#0f766e",colorLight:"#f0fdfa",badge:"M\xc1S POPULAR",usuarios:"Hasta 5 usuarios",features:["Todo lo del plan Mensual","Hasta 5 usuarios por droguer\xeda","Reportes estad\xedsticos avanzados","B\xfasqueda en cosm\xe9ticos INVIMA","Historial RS vencidos (auditor\xeda)","Soporte prioritario"]},{id:"anual",nombre:"Anual",precio:"300.000",periodo:"/ a\xf1o",desc:"La mejor inversi\xf3n. Ahorra $60.000 vs el plan mensual.",color:"#7c3aed",colorLight:"#faf5ff",badge:"MEJOR VALOR",usuarios:"Hasta 10 usuarios",features:["Todo lo del plan Semestral","Hasta 10 usuarios por droguer\xeda","Acceso anticipado a nuevas funciones","Capacitaci\xf3n virtual incluida","Respaldo de datos garantizado","Soporte dedicado 24/7"]}],i=[{n:"01",titulo:"Sube la factura",desc:"Carga el PDF o imagen de tu factura del proveedor. El sistema la procesa autom\xe1ticamente con OCR.",icon:"\uD83D\uDCC4"},{n:"02",titulo:"Validaci\xf3n INVIMA",desc:"Cada producto se cruza en tiempo real con el cat\xe1logo oficial del INVIMA en datos.gov.co.",icon:"\uD83D\uDD0D"},{n:"03",titulo:"Evaluaci\xf3n t\xe9cnica",desc:"El regente revisa, califica defectos y toma la decisi\xf3n de aceptar o rechazar cada \xedtem.",icon:"✅"},{n:"04",titulo:"Acta y Excel",desc:"Se genera autom\xe1ticamente el acta en PDF y el reporte Excel listo para presentar al INVIMA.",icon:"\uD83D\uDCCA"}];function j(){let a=(0,f.useRouter)(),[b,c]=(0,e.useState)(!1);return(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)("style",{children:`
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

        /* SECTION COM\xdaN */
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

        /* POR QU\xc9 */
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
      `}),(0,d.jsxs)("div",{className:"page",children:[(0,d.jsxs)("nav",{className:"nav",children:[(0,d.jsxs)("div",{className:"nav-logo",children:["Solu",(0,d.jsx)("span",{children:"Med"})]}),(0,d.jsxs)("div",{className:"nav-links",children:[(0,d.jsx)("button",{className:"nav-btn nav-btn-ghost",onClick:()=>document.getElementById("planes")?.scrollIntoView({behavior:"smooth"}),children:"Planes"}),(0,d.jsx)("button",{className:"nav-btn nav-btn-ghost",onClick:()=>window.open(g,"_blank"),children:"Contacto"}),(0,d.jsx)("button",{className:"nav-btn nav-btn-primary",onClick:()=>a.push("/login"),children:"Iniciar sesi\xf3n"})]})]}),(0,d.jsxs)("section",{className:"hero",children:[(0,d.jsx)("div",{className:"hero-bg-grid"}),(0,d.jsx)("div",{className:"hero-bg-glow"}),(0,d.jsxs)("div",{className:"hero-content",children:[(0,d.jsxs)("div",{className:`fade-up ${b?"in":""}`,children:[(0,d.jsxs)("div",{className:"hero-badge",children:[(0,d.jsx)("div",{className:"hero-badge-dot"}),"Software para droguer\xedas colombianas"]}),(0,d.jsxs)("h1",{children:["Recepci\xf3n t\xe9cnica",(0,d.jsx)("br",{}),(0,d.jsx)("em",{children:"sin papel, sin errores,"}),(0,d.jsx)("br",{}),"con el INVIMA."]}),(0,d.jsx)("p",{className:"hero-sub",children:"SoluMed automatiza la recepci\xf3n t\xe9cnica de medicamentos: extrae los productos de tu factura, los valida contra el cat\xe1logo oficial del INVIMA y genera el acta lista para firmar — todo en minutos."}),(0,d.jsxs)("div",{className:"hero-btns",children:[(0,d.jsx)("button",{className:"btn-hero-primary",onClick:()=>document.getElementById("planes")?.scrollIntoView({behavior:"smooth"}),children:"Ver planes y precios →"}),(0,d.jsxs)("button",{className:"btn-hero-wa",onClick:()=>window.open(g,"_blank"),children:[(0,d.jsx)("span",{children:"\uD83D\uDCAC"})," Hablar por WhatsApp"]})]})]}),(0,d.jsxs)("div",{className:"hero-mockup fade-up in",style:{transitionDelay:".2s"},children:[(0,d.jsxs)("div",{className:"mock-bar",children:[(0,d.jsx)("div",{className:"mock-dot",style:{background:"#ef4444"}}),(0,d.jsx)("div",{className:"mock-dot",style:{background:"#f59e0b"}}),(0,d.jsx)("div",{className:"mock-dot",style:{background:"#22c55e"}}),(0,d.jsx)("span",{style:{marginLeft:8,fontSize:11,color:"#64748b",fontFamily:"monospace"},children:"Recepci\xf3n t\xe9cnica — FAC-2024-001"})]}),(0,d.jsxs)("div",{className:"mock-screen",children:[[{nom:"CIPROFLOXACINO 500MG",invima:"Vigente",dec:"Acepta"},{nom:"METFORMINA 850MG",invima:"Vigente",dec:"Acepta"},{nom:"AMOXICILINA 500MG",invima:"Vigente",dec:"Acepta"},{nom:"LOSARTAN 50MG",invima:"Vencido",dec:"Rechaza"},{nom:"IBUPROFENO 400MG",invima:"Vigente",dec:"Acepta"}].map((a,b)=>(0,d.jsxs)("div",{className:"mock-line",children:[(0,d.jsx)("span",{style:{color:"#94a3b8",minWidth:20},children:b+1}),(0,d.jsx)("span",{style:{color:"#e2e8f0",flex:1,fontSize:11},children:a.nom}),(0,d.jsx)("span",{className:`tag ${"Vigente"===a.invima?"tag-green":"tag-red"}`,children:a.invima}),(0,d.jsx)("span",{className:`tag ${"Acepta"===a.dec?"tag-green":"tag-red"}`,children:a.dec})]},b)),(0,d.jsxs)("div",{style:{marginTop:12,padding:"8px 0",borderTop:"1px solid rgba(255,255,255,.08)",display:"flex",justifyContent:"space-between"},children:[(0,d.jsx)("span",{style:{color:"#22c55e",fontSize:11,fontFamily:"monospace"},children:"✓ 4 aceptados"}),(0,d.jsx)("span",{style:{color:"#f87171",fontSize:11,fontFamily:"monospace"},children:"✗ 1 rechazado"}),(0,d.jsx)("span",{style:{color:"#3b82f6",fontSize:11,fontFamily:"monospace"},children:"\uD83D\uDCC4 PDF generado"})]})]})]})]})]}),(0,d.jsx)("div",{className:"stats-section",children:(0,d.jsx)("div",{className:"stats-grid",children:[{num:"63",suf:"+",lbl:"Datasets INVIMA integrados"},{num:"100",suf:"%",lbl:"Validaci\xf3n en tiempo real"},{num:"< 3",suf:"min",lbl:"Por factura procesada"},{num:"0",suf:"",lbl:"Papel necesario"}].map((a,b)=>(0,d.jsxs)("div",{className:"stat-item",children:[(0,d.jsxs)("div",{className:"stat-num",children:[a.num,(0,d.jsx)("span",{children:a.suf})]}),(0,d.jsx)("div",{className:"stat-lbl",children:a.lbl})]},b))})}),(0,d.jsx)("section",{className:"section",children:(0,d.jsxs)("div",{className:"section-inner",children:[(0,d.jsx)("div",{className:"section-tag",children:"// c\xf3mo funciona"}),(0,d.jsxs)("h2",{className:"section-title",children:["De la factura al acta",(0,d.jsx)("br",{}),"en 4 pasos"]}),(0,d.jsx)("p",{className:"section-sub",children:"Sin instalaciones complejas. Sin capacitaci\xf3n extensa. Desde el primer d\xeda."}),(0,d.jsx)("div",{className:"pasos-grid",children:i.map((a,b)=>(0,d.jsxs)("div",{className:"paso-card",children:[(0,d.jsx)("div",{className:"paso-n",children:a.n}),(0,d.jsx)("div",{className:"paso-icon",children:a.icon}),(0,d.jsx)("div",{className:"paso-titulo",children:a.titulo}),(0,d.jsx)("div",{className:"paso-desc",children:a.desc})]},b))})]})}),(0,d.jsx)("section",{className:"planes-section",id:"planes",children:(0,d.jsxs)("div",{className:"section-inner",children:[(0,d.jsx)("div",{className:"section-tag",style:{textAlign:"center"},children:"// planes y precios"}),(0,d.jsx)("h2",{className:"section-title",style:{textAlign:"center"},children:"Elige tu plan"}),(0,d.jsxs)("p",{className:"section-sub",style:{textAlign:"center",margin:"0 auto 0"},children:["Sin contratos. Sin permanencia. Cancela cuando quieras.",(0,d.jsx)("br",{}),"Todos los planes incluyen soporte por WhatsApp."]}),(0,d.jsx)("div",{className:"planes-grid",children:h.map(a=>(0,d.jsxs)("div",{className:`plan-card ${"M\xc1S POPULAR"===a.badge?"featured":""}`,style:{borderColor:a.badge?a.color:"#e2e8f0"},children:[a.badge&&(0,d.jsx)("div",{className:"plan-badge",style:{background:a.color},children:a.badge}),(0,d.jsxs)("div",{className:"plan-header",style:{borderBottom:`3px solid ${a.color}`},children:[(0,d.jsx)("div",{className:"plan-nombre",style:{color:a.color},children:a.nombre}),(0,d.jsxs)("div",{className:"plan-precio-wrap",children:[(0,d.jsx)("span",{className:"plan-moneda",style:{color:a.color},children:"$"}),(0,d.jsx)("span",{className:"plan-precio",style:{color:"#0f172a"},children:a.precio})]}),(0,d.jsxs)("div",{className:"plan-periodo",children:[a.periodo," \xb7 COP"]}),(0,d.jsx)("p",{className:"plan-desc",children:a.desc})]}),(0,d.jsxs)("div",{className:"plan-body",children:[(0,d.jsxs)("div",{className:"plan-usuarios",style:{background:a.colorLight,color:a.color},children:[(0,d.jsx)("span",{children:"\uD83D\uDC65"})," ",a.usuarios]}),(0,d.jsx)("ul",{className:"plan-features",children:a.features.map((b,c)=>(0,d.jsxs)("li",{className:"plan-feature",children:[(0,d.jsx)("span",{className:"feature-check",style:{color:a.color},children:"✓"}),b]},c))}),(0,d.jsxs)("button",{className:"plan-cta",style:{background:a.color,color:"white",boxShadow:`0 4px 16px ${a.color}40`},onClick:()=>window.open(`${g}&text=Hola%2C%20quiero%20contratar%20el%20plan%20${encodeURIComponent(a.nombre)}%20de%20SoluMed`,"_blank"),children:[(0,d.jsx)("span",{children:"\uD83D\uDCAC"})," Contratar por WhatsApp"]})]})]},a.id))}),(0,d.jsx)("p",{style:{textAlign:"center",marginTop:32,fontSize:13,color:"#94a3b8"},children:"* Precios en pesos colombianos (COP) \xb7 IVA no incluido \xb7 El plan inicia tras confirmaci\xf3n de pago"})]})}),(0,d.jsx)("section",{className:"section",style:{background:"white"},children:(0,d.jsxs)("div",{className:"section-inner",children:[(0,d.jsx)("div",{className:"section-tag",children:"// por qu\xe9 solumed"}),(0,d.jsxs)("h2",{className:"section-title",children:["Hecho para droguer\xedas",(0,d.jsx)("br",{}),"colombianas"]}),(0,d.jsx)("div",{className:"porque-grid",style:{marginTop:48},children:[{icon:"\uD83C\uDFDB️",color:"#eff6ff",titulo:"API INVIMA oficial",desc:"Consultamos directamente datos.gov.co con los registros sanitarios vigentes del INVIMA. Sin datos desactualizados ni bases propias."},{icon:"\uD83D\uDCCA",color:"#f0fdf4",titulo:"Excel para auditor\xedas",desc:"Genera autom\xe1ticamente el libro Excel con una hoja por mes, listo para presentar ante el INVIMA en una visita de control."},{icon:"\uD83D\uDD12",color:"#faf5ff",titulo:"Multi-droguer\xeda seguro",desc:"Cada droguer\xeda ve \xfanicamente sus propios datos. Sistema de roles: superadmin, administrador y regente de farmacia."},{icon:"\uD83D\uDCC4",color:"#fff7ed",titulo:"Actas en PDF",desc:"Genera el acta t\xe9cnica de recepci\xf3n con espacios de firma, resumen de aceptados/rechazados y c\xf3digo de factura."},{icon:"⚡",color:"#fffbeb",titulo:"OCR inteligente",desc:"Extrae autom\xe1ticamente los productos de la factura (PDF o imagen). Sin digitar nada manualmente."},{icon:"\uD83C\uDDE8\uD83C\uDDF4",color:"#f0fdf4",titulo:"Soporte colombiano",desc:"Atenci\xf3n directa por WhatsApp con el desarrollador. Respuesta r\xe1pida, sin bots, sin tickets internacionales."}].map((a,b)=>(0,d.jsxs)("div",{className:"porque-card",children:[(0,d.jsx)("div",{className:"porque-icon",style:{background:a.color},children:a.icon}),(0,d.jsx)("div",{className:"porque-titulo",children:a.titulo}),(0,d.jsx)("div",{className:"porque-desc",children:a.desc})]},b))})]})}),(0,d.jsxs)("section",{className:"cta-section",children:[(0,d.jsx)("div",{className:"cta-glow"}),(0,d.jsxs)("div",{className:"cta-content",children:[(0,d.jsxs)("h2",{className:"cta-title",children:["\xbfListo para modernizar",(0,d.jsx)("br",{}),"tu droguer\xeda?"]}),(0,d.jsx)("p",{className:"cta-sub",children:"Escr\xedbenos ahora y te ayudamos a crear tu cuenta en minutos."}),(0,d.jsxs)("div",{className:"cta-btns",children:[(0,d.jsxs)("button",{style:{padding:"16px 32px",borderRadius:12,border:"none",cursor:"pointer",background:"#25D366",color:"white",fontFamily:"Sora, sans-serif",fontSize:16,fontWeight:700,display:"flex",alignItems:"center",gap:10,boxShadow:"0 4px 24px rgba(37,211,102,.4)",transition:"all .2s"},onMouseEnter:a=>a.currentTarget.style.transform="translateY(-2px)",onMouseLeave:a=>a.currentTarget.style.transform="none",onClick:()=>window.open(g,"_blank"),children:[(0,d.jsx)("span",{style:{fontSize:20},children:"\uD83D\uDCAC"}),"Escribir por WhatsApp"]}),(0,d.jsx)("button",{style:{padding:"16px 32px",borderRadius:12,cursor:"pointer",background:"transparent",color:"white",border:"1px solid rgba(255,255,255,.3)",fontFamily:"Sora, sans-serif",fontSize:16,fontWeight:600,transition:"all .2s"},onMouseEnter:a=>a.currentTarget.style.background="rgba(255,255,255,.1)",onMouseLeave:a=>a.currentTarget.style.background="transparent",onClick:()=>a.push("/login"),children:"Ya tengo cuenta →"})]}),(0,d.jsx)("div",{style:{marginTop:40,display:"flex",justifyContent:"center",gap:32,flexWrap:"wrap"},children:["Sin permanencia","Soporte incluido","Datos protegidos","Pago por WhatsApp"].map(a=>(0,d.jsxs)("span",{style:{fontSize:13,color:"#64748b",display:"flex",alignItems:"center",gap:6},children:[(0,d.jsx)("span",{style:{color:"#22c55e"},children:"✓"})," ",a]},a))})]})]}),(0,d.jsxs)("footer",{className:"footer",children:[(0,d.jsxs)("div",{className:"footer-logo",children:["Solu",(0,d.jsx)("span",{children:"Med"})]}),(0,d.jsx)("p",{className:"footer-copy",style:{marginTop:8},children:"Software de recepci\xf3n t\xe9cnica para droguer\xedas colombianas \xb7 +57 318 799 3643"}),(0,d.jsxs)("p",{className:"footer-copy",style:{marginTop:4},children:["\xa9 ",new Date().getFullYear()," SoluMed \xb7 Todos los derechos reservados"]})]})]})]})}},62602:(a,b,c)=>{"use strict";c.r(b),c.d(b,{default:()=>d});let d=(0,c(97954).registerClientReference)(function(){throw Error("Attempted to call the default export of \"C:\\\\Users\\\\Steven\\\\Documents\\\\back front recepcion\\\\solumed_front\\\\frontend\\\\src\\\\app\\\\info\\\\page.tsx\" from the server, but it's on the client. It's not possible to invoke a client function from the server, it can only be rendered as a Component or passed to props of a Client Component.")},"C:\\Users\\Steven\\Documents\\back front recepcion\\solumed_front\\frontend\\src\\app\\info\\page.tsx","default")},63033:a=>{"use strict";a.exports=require("next/dist/server/app-render/work-unit-async-storage.external.js")},66728:(a,b,c)=>{"use strict";c.r(b),c.d(b,{GlobalError:()=>D.a,__next_app__:()=>J,handler:()=>L,pages:()=>I,routeModule:()=>K,tree:()=>H});var d=c(49754),e=c(9117),f=c(46595),g=c(32324),h=c(39326),i=c(38928),j=c(20175),k=c(12),l=c(54290),m=c(12696),n=c(82802),o=c(77533),p=c(45229),q=c(32822),r=c(261),s=c(26453),t=c(52474),u=c(26713),v=c(51356),w=c(62685),x=c(36225),y=c(63446),z=c(2762),A=c(45742),B=c(86439),C=c(81170),D=c.n(C),E=c(62506),F=c(91203),G={};for(let a in E)0>["default","tree","pages","GlobalError","__next_app__","routeModule","handler"].indexOf(a)&&(G[a]=()=>E[a]);c.d(b,G);let H={children:["",{children:["info",{children:["__PAGE__",{},{page:[()=>Promise.resolve().then(c.bind(c,62602)),"C:\\Users\\Steven\\Documents\\back front recepcion\\solumed_front\\frontend\\src\\app\\info\\page.tsx"]}]},{}]},{layout:[()=>Promise.resolve().then(c.bind(c,51472)),"C:\\Users\\Steven\\Documents\\back front recepcion\\solumed_front\\frontend\\src\\app\\layout.tsx"],"global-error":[()=>Promise.resolve().then(c.t.bind(c,81170,23)),"next/dist/client/components/builtin/global-error.js"],"not-found":[()=>Promise.resolve().then(c.t.bind(c,87028,23)),"next/dist/client/components/builtin/not-found.js"],forbidden:[()=>Promise.resolve().then(c.t.bind(c,90461,23)),"next/dist/client/components/builtin/forbidden.js"],unauthorized:[()=>Promise.resolve().then(c.t.bind(c,32768,23)),"next/dist/client/components/builtin/unauthorized.js"]}]}.children,I=["C:\\Users\\Steven\\Documents\\back front recepcion\\solumed_front\\frontend\\src\\app\\info\\page.tsx"],J={require:c,loadChunk:()=>Promise.resolve()},K=new d.AppPageRouteModule({definition:{kind:e.RouteKind.APP_PAGE,page:"/info/page",pathname:"/info",bundlePath:"",filename:"",appPaths:[]},userland:{loaderTree:H},distDir:".next",relativeProjectDir:""});async function L(a,b,d){var C;let G="/info/page";"/index"===G&&(G="/");let M=(0,h.getRequestMeta)(a,"postponed"),N=(0,h.getRequestMeta)(a,"minimalMode"),O=await K.prepare(a,b,{srcPage:G,multiZoneDraftMode:!1});if(!O)return b.statusCode=400,b.end("Bad Request"),null==d.waitUntil||d.waitUntil.call(d,Promise.resolve()),null;let{buildId:P,query:Q,params:R,parsedUrl:S,pageIsDynamic:T,buildManifest:U,nextFontManifest:V,reactLoadableManifest:W,serverActionsManifest:X,clientReferenceManifest:Y,subresourceIntegrityManifest:Z,prerenderManifest:$,isDraftMode:_,resolvedPathname:aa,revalidateOnlyGenerated:ab,routerServerContext:ac,nextConfig:ad,interceptionRoutePatterns:ae}=O,af=S.pathname||"/",ag=(0,r.normalizeAppPath)(G),{isOnDemandRevalidate:ah}=O,ai=K.match(af,$),aj=!!$.routes[aa],ak=!!(ai||aj||$.routes[ag]),al=a.headers["user-agent"]||"",am=(0,u.getBotType)(al),an=(0,p.isHtmlBotRequest)(a),ao=(0,h.getRequestMeta)(a,"isPrefetchRSCRequest")??"1"===a.headers[t.NEXT_ROUTER_PREFETCH_HEADER],ap=(0,h.getRequestMeta)(a,"isRSCRequest")??!!a.headers[t.RSC_HEADER],aq=(0,s.getIsPossibleServerAction)(a),ar=(0,m.checkIsAppPPREnabled)(ad.experimental.ppr)&&(null==(C=$.routes[ag]??$.dynamicRoutes[ag])?void 0:C.renderingMode)==="PARTIALLY_STATIC",as=!1,at=!1,au=ar?M:void 0,av=ar&&ap&&!ao,aw=(0,h.getRequestMeta)(a,"segmentPrefetchRSCRequest"),ax=!al||(0,p.shouldServeStreamingMetadata)(al,ad.htmlLimitedBots);an&&ar&&(ak=!1,ax=!1);let ay=!0===K.isDev||!ak||"string"==typeof M||av,az=an&&ar,aA=null;_||!ak||ay||aq||au||av||(aA=aa);let aB=aA;!aB&&K.isDev&&(aB=aa),K.isDev||_||!ak||!ap||av||(0,k.d)(a.headers);let aC={...E,tree:H,pages:I,GlobalError:D(),handler:L,routeModule:K,__next_app__:J};X&&Y&&(0,o.setReferenceManifestsSingleton)({page:G,clientReferenceManifest:Y,serverActionsManifest:X,serverModuleMap:(0,q.createServerModuleMap)({serverActionsManifest:X})});let aD=a.method||"GET",aE=(0,g.getTracer)(),aF=aE.getActiveScopeSpan();try{let f=K.getVaryHeader(aa,ae);b.setHeader("Vary",f);let k=async(c,d)=>{let e=new l.NodeNextRequest(a),f=new l.NodeNextResponse(b);return K.render(e,f,d).finally(()=>{if(!c)return;c.setAttributes({"http.status_code":b.statusCode,"next.rsc":!1});let d=aE.getRootSpanAttributes();if(!d)return;if(d.get("next.span_type")!==i.BaseServerSpan.handleRequest)return void console.warn(`Unexpected root span type '${d.get("next.span_type")}'. Please report this Next.js issue https://github.com/vercel/next.js`);let e=d.get("next.route");if(e){let a=`${aD} ${e}`;c.setAttributes({"next.route":e,"http.route":e,"next.span_name":a}),c.updateName(a)}else c.updateName(`${aD} ${a.url}`)})},m=async({span:e,postponed:f,fallbackRouteParams:g})=>{let i={query:Q,params:R,page:ag,sharedContext:{buildId:P},serverComponentsHmrCache:(0,h.getRequestMeta)(a,"serverComponentsHmrCache"),fallbackRouteParams:g,renderOpts:{App:()=>null,Document:()=>null,pageConfig:{},ComponentMod:aC,Component:(0,j.T)(aC),params:R,routeModule:K,page:G,postponed:f,shouldWaitOnAllReady:az,serveStreamingMetadata:ax,supportsDynamicResponse:"string"==typeof f||ay,buildManifest:U,nextFontManifest:V,reactLoadableManifest:W,subresourceIntegrityManifest:Z,serverActionsManifest:X,clientReferenceManifest:Y,setIsrStatus:null==ac?void 0:ac.setIsrStatus,dir:c(33873).join(process.cwd(),K.relativeProjectDir),isDraftMode:_,isRevalidate:ak&&!f&&!av,botType:am,isOnDemandRevalidate:ah,isPossibleServerAction:aq,assetPrefix:ad.assetPrefix,nextConfigOutput:ad.output,crossOrigin:ad.crossOrigin,trailingSlash:ad.trailingSlash,previewProps:$.preview,deploymentId:ad.deploymentId,enableTainting:ad.experimental.taint,htmlLimitedBots:ad.htmlLimitedBots,devtoolSegmentExplorer:ad.experimental.devtoolSegmentExplorer,reactMaxHeadersLength:ad.reactMaxHeadersLength,multiZoneDraftMode:!1,incrementalCache:(0,h.getRequestMeta)(a,"incrementalCache"),cacheLifeProfiles:ad.experimental.cacheLife,basePath:ad.basePath,serverActions:ad.experimental.serverActions,...as?{nextExport:!0,supportsDynamicResponse:!1,isStaticGeneration:!0,isRevalidate:!0,isDebugDynamicAccesses:as}:{},experimental:{isRoutePPREnabled:ar,expireTime:ad.expireTime,staleTimes:ad.experimental.staleTimes,cacheComponents:!!ad.experimental.cacheComponents,clientSegmentCache:!!ad.experimental.clientSegmentCache,clientParamParsing:!!ad.experimental.clientParamParsing,dynamicOnHover:!!ad.experimental.dynamicOnHover,inlineCss:!!ad.experimental.inlineCss,authInterrupts:!!ad.experimental.authInterrupts,clientTraceMetadata:ad.experimental.clientTraceMetadata||[]},waitUntil:d.waitUntil,onClose:a=>{b.on("close",a)},onAfterTaskError:()=>{},onInstrumentationRequestError:(b,c,d)=>K.onRequestError(a,b,d,ac),err:(0,h.getRequestMeta)(a,"invokeError"),dev:K.isDev}},l=await k(e,i),{metadata:m}=l,{cacheControl:n,headers:o={},fetchTags:p}=m;if(p&&(o[y.NEXT_CACHE_TAGS_HEADER]=p),a.fetchMetrics=m.fetchMetrics,ak&&(null==n?void 0:n.revalidate)===0&&!K.isDev&&!ar){let a=m.staticBailoutInfo,b=Object.defineProperty(Error(`Page changed from static to dynamic at runtime ${aa}${(null==a?void 0:a.description)?`, reason: ${a.description}`:""}
see more here https://nextjs.org/docs/messages/app-static-to-dynamic-error`),"__NEXT_ERROR_CODE",{value:"E132",enumerable:!1,configurable:!0});if(null==a?void 0:a.stack){let c=a.stack;b.stack=b.message+c.substring(c.indexOf("\n"))}throw b}return{value:{kind:v.CachedRouteKind.APP_PAGE,html:l,headers:o,rscData:m.flightData,postponed:m.postponed,status:m.statusCode,segmentData:m.segmentData},cacheControl:n}},o=async({hasResolved:c,previousCacheEntry:f,isRevalidating:g,span:i})=>{let j,k=!1===K.isDev,l=c||b.writableEnded;if(ah&&ab&&!f&&!N)return(null==ac?void 0:ac.render404)?await ac.render404(a,b):(b.statusCode=404,b.end("This page could not be found")),null;if(ai&&(j=(0,w.parseFallbackField)(ai.fallback)),j===w.FallbackMode.PRERENDER&&(0,u.isBot)(al)&&(!ar||an)&&(j=w.FallbackMode.BLOCKING_STATIC_RENDER),(null==f?void 0:f.isStale)===-1&&(ah=!0),ah&&(j!==w.FallbackMode.NOT_FOUND||f)&&(j=w.FallbackMode.BLOCKING_STATIC_RENDER),!N&&j!==w.FallbackMode.BLOCKING_STATIC_RENDER&&aB&&!l&&!_&&T&&(k||!aj)){let b;if((k||ai)&&j===w.FallbackMode.NOT_FOUND)throw new B.NoFallbackError;if(ar&&!ap){let c="string"==typeof(null==ai?void 0:ai.fallback)?ai.fallback:k?ag:null;if(b=await K.handleResponse({cacheKey:c,req:a,nextConfig:ad,routeKind:e.RouteKind.APP_PAGE,isFallback:!0,prerenderManifest:$,isRoutePPREnabled:ar,responseGenerator:async()=>m({span:i,postponed:void 0,fallbackRouteParams:k||at?(0,n.u)(ag):null}),waitUntil:d.waitUntil}),null===b)return null;if(b)return delete b.cacheControl,b}}let o=ah||g||!au?void 0:au;if(as&&void 0!==o)return{cacheControl:{revalidate:1,expire:void 0},value:{kind:v.CachedRouteKind.PAGES,html:x.default.EMPTY,pageData:{},headers:void 0,status:void 0}};let p=T&&ar&&((0,h.getRequestMeta)(a,"renderFallbackShell")||at)?(0,n.u)(af):null;return m({span:i,postponed:o,fallbackRouteParams:p})},p=async c=>{var f,g,i,j,k;let l,n=await K.handleResponse({cacheKey:aA,responseGenerator:a=>o({span:c,...a}),routeKind:e.RouteKind.APP_PAGE,isOnDemandRevalidate:ah,isRoutePPREnabled:ar,req:a,nextConfig:ad,prerenderManifest:$,waitUntil:d.waitUntil});if(_&&b.setHeader("Cache-Control","private, no-cache, no-store, max-age=0, must-revalidate"),K.isDev&&b.setHeader("Cache-Control","no-store, must-revalidate"),!n){if(aA)throw Object.defineProperty(Error("invariant: cache entry required but not generated"),"__NEXT_ERROR_CODE",{value:"E62",enumerable:!1,configurable:!0});return null}if((null==(f=n.value)?void 0:f.kind)!==v.CachedRouteKind.APP_PAGE)throw Object.defineProperty(Error(`Invariant app-page handler received invalid cache entry ${null==(i=n.value)?void 0:i.kind}`),"__NEXT_ERROR_CODE",{value:"E707",enumerable:!1,configurable:!0});let p="string"==typeof n.value.postponed;ak&&!av&&(!p||ao)&&(N||b.setHeader("x-nextjs-cache",ah?"REVALIDATED":n.isMiss?"MISS":n.isStale?"STALE":"HIT"),b.setHeader(t.NEXT_IS_PRERENDER_HEADER,"1"));let{value:q}=n;if(au)l={revalidate:0,expire:void 0};else if(N&&ap&&!ao&&ar)l={revalidate:0,expire:void 0};else if(!K.isDev)if(_)l={revalidate:0,expire:void 0};else if(ak){if(n.cacheControl)if("number"==typeof n.cacheControl.revalidate){if(n.cacheControl.revalidate<1)throw Object.defineProperty(Error(`Invalid revalidate configuration provided: ${n.cacheControl.revalidate} < 1`),"__NEXT_ERROR_CODE",{value:"E22",enumerable:!1,configurable:!0});l={revalidate:n.cacheControl.revalidate,expire:(null==(j=n.cacheControl)?void 0:j.expire)??ad.expireTime}}else l={revalidate:y.CACHE_ONE_YEAR,expire:void 0}}else b.getHeader("Cache-Control")||(l={revalidate:0,expire:void 0});if(n.cacheControl=l,"string"==typeof aw&&(null==q?void 0:q.kind)===v.CachedRouteKind.APP_PAGE&&q.segmentData){b.setHeader(t.NEXT_DID_POSTPONE_HEADER,"2");let c=null==(k=q.headers)?void 0:k[y.NEXT_CACHE_TAGS_HEADER];N&&ak&&c&&"string"==typeof c&&b.setHeader(y.NEXT_CACHE_TAGS_HEADER,c);let d=q.segmentData.get(aw);return void 0!==d?(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.fromStatic(d,t.RSC_CONTENT_TYPE_HEADER),cacheControl:n.cacheControl}):(b.statusCode=204,(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.EMPTY,cacheControl:n.cacheControl}))}let r=(0,h.getRequestMeta)(a,"onCacheEntry");if(r&&await r({...n,value:{...n.value,kind:"PAGE"}},{url:(0,h.getRequestMeta)(a,"initURL")}))return null;if(p&&au)throw Object.defineProperty(Error("Invariant: postponed state should not be present on a resume request"),"__NEXT_ERROR_CODE",{value:"E396",enumerable:!1,configurable:!0});if(q.headers){let a={...q.headers};for(let[c,d]of(N&&ak||delete a[y.NEXT_CACHE_TAGS_HEADER],Object.entries(a)))if(void 0!==d)if(Array.isArray(d))for(let a of d)b.appendHeader(c,a);else"number"==typeof d&&(d=d.toString()),b.appendHeader(c,d)}let s=null==(g=q.headers)?void 0:g[y.NEXT_CACHE_TAGS_HEADER];if(N&&ak&&s&&"string"==typeof s&&b.setHeader(y.NEXT_CACHE_TAGS_HEADER,s),!q.status||ap&&ar||(b.statusCode=q.status),!N&&q.status&&F.RedirectStatusCode[q.status]&&ap&&(b.statusCode=200),p&&b.setHeader(t.NEXT_DID_POSTPONE_HEADER,"1"),ap&&!_){if(void 0===q.rscData){if(q.postponed)throw Object.defineProperty(Error("Invariant: Expected postponed to be undefined"),"__NEXT_ERROR_CODE",{value:"E372",enumerable:!1,configurable:!0});return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:q.html,cacheControl:av?{revalidate:0,expire:void 0}:n.cacheControl})}return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.fromStatic(q.rscData,t.RSC_CONTENT_TYPE_HEADER),cacheControl:n.cacheControl})}let u=q.html;if(!p||N||ap)return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:n.cacheControl});if(as)return u.push(new ReadableStream({start(a){a.enqueue(z.ENCODED_TAGS.CLOSED.BODY_AND_HTML),a.close()}})),(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:{revalidate:0,expire:void 0}});let w=new TransformStream;return u.push(w.readable),m({span:c,postponed:q.postponed,fallbackRouteParams:null}).then(async a=>{var b,c;if(!a)throw Object.defineProperty(Error("Invariant: expected a result to be returned"),"__NEXT_ERROR_CODE",{value:"E463",enumerable:!1,configurable:!0});if((null==(b=a.value)?void 0:b.kind)!==v.CachedRouteKind.APP_PAGE)throw Object.defineProperty(Error(`Invariant: expected a page response, got ${null==(c=a.value)?void 0:c.kind}`),"__NEXT_ERROR_CODE",{value:"E305",enumerable:!1,configurable:!0});await a.value.html.pipeTo(w.writable)}).catch(a=>{w.writable.abort(a).catch(a=>{console.error("couldn't abort transformer",a)})}),(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:{revalidate:0,expire:void 0}})};if(!aF)return await aE.withPropagatedContext(a.headers,()=>aE.trace(i.BaseServerSpan.handleRequest,{spanName:`${aD} ${a.url}`,kind:g.SpanKind.SERVER,attributes:{"http.method":aD,"http.target":a.url}},p));await p(aF)}catch(b){throw b instanceof B.NoFallbackError||await K.onRequestError(a,b,{routerKind:"App Router",routePath:G,routeType:"render",revalidateReason:(0,f.c)({isRevalidate:ak,isOnDemandRevalidate:ah})},ac),b}}},86439:a=>{"use strict";a.exports=require("next/dist/shared/lib/no-fallback-error.external")},98171:(a,b,c)=>{Promise.resolve().then(c.bind(c,43600))}};var b=require("../../webpack-runtime.js");b.C(a);var c=b.X(0,[699,498],()=>b(b.s=66728));module.exports=c})();