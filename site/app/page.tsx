import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Best Gift Search — Multi-Agent Gift Concierge",
  description: "A visual walkthrough of the explainable Best Gift Search AI agent.",
};

const gifts = [
  { rank: "01", match: 94, icon: "☕", merchant: "ROAM & ROAST", name: "Travel Coffee Ritual Kit", description: "A compact pour-over set, hand grinder, and two origin coffees for mornings anywhere.", reasons: ["Matches coffee + travel", "Complete landed cost"], price: "$68" },
  { rank: "02", match: 89, icon: "✦", merchant: "ATLAS GOODS", name: "Personalized Travel Journal", description: "Refillable linen journal with a subtle monogram and pockets for tickets and keepsakes.", reasons: ["Thoughtful personalization", "Easy international delivery"], price: "$54" },
  { rank: "03", match: 86, icon: "◒", merchant: "STUDIO NOMA", name: "Ceramic Tasting Set", description: "Two handmade tasting cups designed to bring a favorite café ritual home.", reasons: ["Strong recipient fit", "Independent maker"], price: "$72" },
  { rank: "04", match: 82, icon: "⌁", merchant: "FIELD NOTES", name: "Weekend City Explorer", description: "A beautifully illustrated guide and prompt deck for planning memorable micro-adventures.", reasons: ["Experience-led gift", "Comfortably in budget"], price: "$39" },
];

const phases = [
  ["01", "Understand", "Recipient profile"],
  ["02", "Explore", "Parallel search"],
  ["03", "Compare", "Delivered value"],
  ["04", "Reflect", "Explain matches"],
];

export default function Home() {
  return <main>
    <header><a className="brand" href="#top">Best Gift Search<span>✦</span></a><nav><a href="#results">Demo</a><a href="#architecture">How it works</a><a className="github" href="https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent">GitHub ↗</a></nav></header>
    <section className="hero" id="top">
      <p className="eyebrow">MULTI-AGENT GIFT CONCIERGE</p>
      <h1>Find the gift that feels<br/><em>exactly right.</em></h1>
      <p className="intro">Tell us who they are. Specialized agents understand, search, compare, and explain the best matches—without the endless tabs.</p>
      <div className="searchbox"><p>A thoughtful birthday gift for my sister who loves coffee and travel, under $80</p><div><span>Deliver to&nbsp; <b>US⌄</b></span><a href="#results">See demo results →</a></div></div>
      <p className="demo-note">Interactive showcase · the repository includes the live FastAPI + WebSocket application</p>
    </section>
    <section className="process" id="architecture">{phases.map(([n,title,note])=><div key={n}><span>{n}</span><b>{title}</b><small>{note}</small></div>)}</section>
    <section className="results" id="results">
      <div className="sectionhead"><div><p className="eyebrow">CURATED FOR YOU</p><h2>Four thoughtful ways to bring her coffee ritual on every journey.</h2></div><p>4 standout ideas · under USD 80</p></div>
      <div className="grid">{gifts.map(g=><article key={g.rank}><div className={`photo p${g.rank}`}><span className="symbol">{g.icon}</span><span className="match">#{g.rank} · {g.match}% match</span></div><div className="cardbody"><small>{g.merchant} · ★ 4.8</small><h3>{g.name}</h3><p>{g.description}</p><ul>{g.reasons.map(r=><li key={r}>{r}</li>)}</ul><div className="price"><b>{g.price}</b><span>Delivered total</span></div></div></article>)}</div>
    </section>
    <section className="rubric"><div><p className="eyebrow">AUTOMATED QUALITY RUBRIC</p><h2>78.2<small>/100 · PASSED</small></h2></div>{[["Relevance",84],["Budget fit",100],["Diversity",62],["Explainability",67]].map(([label,value])=><div className="meter" key={String(label)}><span>{label}</span><b>{value}</b><i><em style={{width:`${value}%`}}/></i></div>)}</section>
    <section className="agentlog"><div><p className="eyebrow">EXPLAINABLE BY DESIGN</p><h2>See how the answer was made.</h2><p>Every search preserves a replayable think → act → observe → reflect trace, compact checkpoints, and explicit scoring reasons.</p></div><ol><li><b>Recipient Agent</b><span>Extracted coffee, travel, birthday, and thoughtful intent.</span></li><li><b>Catalog Agent</b><span>Retrieved and ranked candidates across categories.</span></li><li><b>Value Agent</b><span>Compared product price, shipping, rating, and budget fit.</span></li><li><b>Orchestrator</b><span>Reflected on diversity and produced the final shortlist.</span></li></ol></section>
    <section className="cta"><p className="eyebrow">RUN THE REAL APPLICATION</p><h2>Backend, live agent stream, memory, evaluation—all included.</h2><p>Clone the repository and follow the README for Docker or local setup. Deterministic demo mode requires no API key.</p><a href="https://github.com/Irenezhangtt/BestGiftSearch-AI-Agent">View source & setup guide ↗</a></section>
    <footer><b>Best Gift Search ✦</b><span>Explainable recommendations · No sponsored ranking</span></footer>
  </main>;
}
