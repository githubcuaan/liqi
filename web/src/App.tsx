import { useEffect, useState } from "react";
import {
  Activity, ArrowRight, BookOpen, ChartNoAxesCombined, ChevronRight,
  CircleHelp, Compass, Download, FlaskConical, Layers3, Menu,
  Moon, Search, ShieldAlert, Sparkles, Sun, Swords, Target, X,
} from "lucide-react";
import brandMark from "../../public/assets/liqily-logo.png";
import brandLockup from "../../public/assets/liqily.png";

type Hero = {
  hero_id: string; hero_name: string; pick_candidate: boolean;
  ban_candidate: boolean; seen_in_prediction_train: boolean;
};
type Overview = {
  total_games: number; total_teams: number; unique_heroes: number;
  dataset_version: string; draft_version: string; prediction_model: string;
};
type Page = "home" | "mining" | "draft" | "prediction" | "about";
type Params = { min_support: number; min_confidence: number; min_lift: number; max_heroes: number };
type Rule = {
  antecedent_label: string; consequent_label: string;
  support: number; confidence: number; lift: number;
};
type MiningResult = {
  algorithm: string; total_transactions: number; execution_time_sec: number;
  frequent_itemsets_count: number; total_rules_count: number;
  win_rules_count: number; lose_rules_count: number;
  rules: Rule[]; truncated: boolean;
};
type DraftResult = {
  action: string; method: string; score_type: string; returned_count: number;
  popularity_tiebreak_for_all_zero_scores: boolean;
  recommendations: {
    rank: number; hero_id: string; hero_name: string; score: number;
    evidence: { train_lineup_count?: number; train_ban_count?: number; train_games?: number };
  }[];
};
type PredictionResult = {
  team_a_win_probability: number; side_baseline_probability: number;
  predicted_winner: string; unknown_categories: {
    team_a_heroes: string[]; team_b_heroes: string[]; patch_id: string | null;
  }; model_version: string; limitations: string;
};
type Composition = {
  hero_ids: string[]; heroes: string[]; matches: number; wins: number;
  win_rate: number; rating: string;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init, headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : `Yêu cầu thất bại (${response.status})`);
  }
  return response.json() as Promise<T>;
}
const post = <T,>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
const nav: { id: Page; title: string; icon: typeof Compass }[] = [
  { id: "home", title: "Tổng quan", icon: Compass },
  { id: "mining", title: "Khám phá dữ liệu", icon: ChartNoAxesCombined },
  { id: "draft", title: "Trợ lý cấm chọn", icon: Swords },
  { id: "prediction", title: "Dự đoán trận đấu", icon: Target },
  { id: "about", title: "Về nghiên cứu", icon: BookOpen },
];

function HeroPicker({
  heroes, selected, excluded, max, onChange, label,
}: {
  heroes: Hero[]; selected: string[]; excluded: string[]; max: number;
  onChange: (ids: string[]) => void; label: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const available = heroes.filter(hero =>
    !selected.includes(hero.hero_id) && !excluded.includes(hero.hero_id)
    && hero.hero_name.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 10);
  const names = new Map(heroes.map(hero => [hero.hero_id, hero.hero_name]));
  return <div className="picker">
    <div className="picker-header"><span>{label}</span><span className="muted">{selected.length}/{max}</span></div>
    <div className="chips">{selected.map(id =>
      <button className="chip" key={id} onClick={() => onChange(selected.filter(item => item !== id))} aria-label={`Xóa ${names.get(id)}`}>
        <span className="hero-dot">{(names.get(id) || "?").slice(0, 1)}</span>{names.get(id) || id}<X size={13} />
      </button>
    )}{selected.length === 0 && <span className="empty-hint">Chưa chọn tướng</span>}</div>
    {selected.length < max && <div className="picker-input">
      <Search size={16} />
      <input value={query} onFocus={() => setOpen(true)} onClick={() => setOpen(true)} onChange={event => { setQuery(event.target.value); setOpen(true); }}
        onBlur={() => window.setTimeout(() => setOpen(false), 160)} placeholder="Tìm tên tướng..." aria-label={`Tìm tướng cho ${label}`} />
      {open && <div className="picker-options" role="listbox">
        {available.length ? available.map(hero =>
          <button type="button" role="option" aria-selected={false} key={hero.hero_id}
            onMouseDown={event => event.preventDefault()}
            onClick={() => { onChange([...selected, hero.hero_id]); setQuery(""); setOpen(false); }}>
            <span className="hero-dot">{hero.hero_name.slice(0, 1)}</span>{hero.hero_name}
          </button>
        ) : <span className="option-empty">Không tìm thấy tướng</span>}
      </div>}
    </div>}
  </div>;
}

function Header({ title, subtitle, eyebrow }: { title: string; subtitle: string; eyebrow: string }) {
  return <div className="page-heading"><span className="eyebrow">{eyebrow}</span>
    <h1>{title}</h1><p>{subtitle}</p></div>;
}

function Home({ overview, go }: { overview: Overview | null; go: (page: Page) => void }) {
  return <>
    <section className="hero-section">
      <div className="hero-copy">
        <span className="eyebrow"><span className="pulse" /> LIQILY · ARENA INTELLIGENCE</span>
        <h1>Hiểu đội hình.<br /><em>Đọc vị trận đấu.</em></h1>
        <p>Một không gian khám phá dữ liệu Liên Quân: từ combo tướng, gợi ý cấm chọn đến thử nghiệm dự đoán sau draft.</p>
        <div className="hero-actions">
          <button className="btn primary" onClick={() => go("draft")}>Bắt đầu khám phá <ArrowRight size={17} /></button>
          <button className="btn subtle" onClick={() => go("about")}>Về dữ liệu <ChevronRight size={17} /></button>
        </div>
      </div>
      <div className="brand-visual"><img src={brandLockup} alt="Liqily Esports Analytics" /></div>
    </section>
    <section className="stat-strip">
      <div><span>TRẬN ĐẤU TRAIN</span><strong>{overview?.total_games ?? "—"}</strong><small>Đấu Trường Danh Vọng 2026</small></div>
      <div><span>ĐỘI HÌNH</span><strong>{overview?.total_teams ?? "—"}</strong><small>Transaction phân tích</small></div>
      <div><span>TƯỚNG XUẤT HIỆN</span><strong>{overview?.unique_heroes ?? "—"}</strong><small>Trong tập huấn luyện</small></div>
    </section>
    <div className="section-heading"><span className="eyebrow">BỘ CÔNG CỤ</span><h2>Ba góc nhìn. Một bức tranh.</h2></div>
    <div className="feature-grid">
      {[
        { page: "mining" as Page, number: "01", icon: ChartNoAxesCombined, title: "Khám phá đội hình",
          text: "Tìm combo tướng thường đi cùng nhau, đọc luật kết hợp và so sánh Apriori với FP-Growth.", tag: "ASSOCIATION MINING" },
        { page: "draft" as Page, number: "02", icon: Swords, title: "Trợ lý cấm chọn",
          text: "Gợi ý pick theo tương đồng đồng đội và ban theo tần suất quan sát trong tập train.", tag: "PICK / BAN" },
        { page: "prediction" as Page, number: "03", icon: Target, title: "Dự đoán sau draft",
          text: "Thử nghiệm xác suất thắng khi đã biết đầy đủ hai đội hình, phe và phiên bản patch.", tag: "RESEARCH DEMO" },
      ].map(feature => <button className="feature-card" key={feature.number} onClick={() => go(feature.page)}>
        <div className="feature-top"><span className="feature-icon"><feature.icon size={23} /></span><span className="feature-number">{feature.number}</span></div>
        <span className="eyebrow">{feature.tag}</span><h3>{feature.title}</h3><p>{feature.text}</p>
        <span className="feature-link">Khám phá <ArrowRight size={16} /></span>
      </button>)}
    </div>
    <div className="notice"><ShieldAlert size={21} /><p><strong>Đọc dữ liệu một cách cẩn trọng.</strong> Luật kết hợp không chứng minh quan hệ nhân quả; điểm gợi ý không phải xác suất thắng. Mô hình dự đoán chưa vượt baseline trên tập test.</p></div>
  </>;
}

function Mining({ heroes }: { heroes: Hero[] }) {
  const [algorithm, setAlgorithm] = useState<"apriori" | "fpgrowth">("fpgrowth");
  const [params, setParams] = useState<Params>({ min_support: 0.01, min_confidence: 0.5, min_lift: 1, max_heroes: 5 });
  const [result, setResult] = useState<MiningResult | null>(null);
  const [comparison, setComparison] = useState<Record<string, any> | null>(null);
  const [compositions, setCompositions] = useState<Composition[]>([]);
  const [comboSize, setComboSize] = useState("all");
  const [minMatches, setMinMatches] = useState(5);
  const [selectedHeroes, setSelectedHeroes] = useState<string[]>([]);
  const [selectedCombo, setSelectedCombo] = useState<Composition | null>(null);
  const [tab, setTab] = useState<"rules" | "combos" | "compare">("rules");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const query = new URLSearchParams({ min_matches: String(minMatches) });
    if (comboSize !== "all") query.set("size", comboSize);
    if (selectedHeroes.length >= 2) selectedHeroes.forEach(id => query.append("hero_ids", id));
    api<{ compositions: Composition[]; selected: Composition | null }>(`/compositions?${query}`)
      .then(data => { setCompositions(data.compositions); setSelectedCombo(data.selected); })
      .catch(err => setError(err.message));
  }, [comboSize, minMatches, selectedHeroes]);
  async function run(compare = false) {
    setBusy(true); setError("");
    try {
      if (compare) { setComparison(await post("/mining/compare", params)); setTab("compare"); }
      else { setResult(await post("/mining/run", { ...params, algorithm })); setTab("rules"); }
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  const reportParams = new URLSearchParams(
    Object.entries(params).map(([key, value]) => [key, String(value)])
  );
  const reportUrl = result && `/api/v1/reports/${algorithm}_rules.csv?${reportParams}`;
  return <>
    <Header eyebrow="01 / DATA DISCOVERY" title="Khám phá đội hình"
      subtitle="Đọc những mẫu xuất hiện trong dữ liệu, không suy diễn quan hệ nhân quả." />
    <div className="layout-two"><div className="panel control-panel">
      <h3><FlaskConical size={19} /> Thiết lập phân tích</h3>
      <label>Thuật toán <select value={algorithm} onChange={e => { setAlgorithm(e.target.value as typeof algorithm); setResult(null); }}>
        <option value="fpgrowth">FP-Growth</option><option value="apriori">Apriori</option>
      </select></label>
      {([
        ["min_support", "Support tối thiểu", 0.01, 1, 0.01],
        ["min_confidence", "Confidence tối thiểu", 0, 1, 0.05],
        ["min_lift", "Lift tối thiểu", 0, 10, 0.1],
        ["max_heroes", "Số tướng tối đa", 2, 5, 1],
      ] as const).map(([key, title, min, max, step]) =>
        <label key={key}>{title}<input type="number" min={min} max={max} step={step} value={params[key]}
          onChange={event => { setParams({ ...params, [key]: Number(event.target.value) }); setResult(null); setComparison(null); }} /></label>
      )}
      <button className="btn primary full" onClick={() => run()} disabled={busy}>{busy ? "Đang phân tích..." : "Chạy phân tích"} <ArrowRight size={16} /></button>
      <button className="btn outline full" onClick={() => run(true)} disabled={busy}>So sánh hai thuật toán</button>
      <p className="small muted">Chỉ dùng 462 transaction từ 231 ván train. Support được tính theo đội, không theo trận.</p>
    </div><div className="panel result-panel">
      <div className="panel-title"><div><span className="eyebrow">KẾT QUẢ</span><h2>Góc nhìn dữ liệu</h2></div>
        {reportUrl && tab === "rules" && <a className="btn outline small-btn" href={reportUrl}><Download size={15} /> CSV</a>}
        {comparison && tab === "compare" && <a className="btn outline small-btn"
          href={`/api/v1/reports/comparison.csv?${reportParams}`}><Download size={15} /> CSV</a>}</div>
      <div className="tabs" role="tablist">
        {([["rules", "Luật kết hợp"], ["combos", "Combo quan sát"], ["compare", "So sánh"]] as const).map(([id, title]) =>
          <button role="tab" aria-selected={tab === id} className={tab === id ? "active" : ""} key={id} onClick={() => setTab(id)}>{title}</button>)}
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      {tab === "rules" && (result ? <>
        <div className="mini-stats"><div><strong>{result.frequent_itemsets_count}</strong><span>Tập phổ biến</span></div>
          <div><strong>{result.win_rules_count + result.lose_rules_count}</strong><span>Luật → kết quả</span></div>
          <div><strong>{result.execution_time_sec.toFixed(3)}s</strong><span>Thời gian</span></div></div>
        {result.rules.length === 0 && <p className="empty-hint">Không có luật tướng → kết quả ở ngưỡng này. Thử hạ support.</p>}
        <div className="table-wrap"><table><thead><tr><th>Điều kiện</th><th>Kết quả</th><th>Support</th><th>Confidence</th><th>Lift</th></tr></thead>
          <tbody>{result.rules.filter(row => row.consequent_label.includes("Kết quả")).slice(0, 40).map((row, index) =>
            <tr key={index}><td>{row.antecedent_label}</td><td><span className="table-tag">{row.consequent_label}</span></td>
              <td>{percent(row.support)}</td><td>{percent(row.confidence)}</td><td>{row.lift.toFixed(2)}</td></tr>)}</tbody></table></div>
        {result.truncated && <p className="small muted">Bảng xem trước tối đa 300 dòng. Tải CSV để xem đầy đủ.</p>}
      </> : <div className="empty-state"><ChartNoAxesCombined size={36} /><h3>Chưa chạy phân tích</h3><p>Chọn ngưỡng và nhấn “Chạy phân tích” để xem luật.</p></div>)}
      {tab === "combos" && <div>
        <div className="combo-filters"><label>Kích thước <select value={comboSize} onChange={e => setComboSize(e.target.value)}>
          <option value="all">Tất cả</option>{[2,3,4,5].map(size => <option key={size} value={size}>{size} tướng</option>)}
        </select></label><label>Số trận tối thiểu <input type="number" min="1" max="462" value={minMatches}
          onChange={e => setMinMatches(Math.max(1, Math.min(462, Number(e.target.value) || 1)))} /></label></div>
        <HeroPicker heroes={heroes} label="Tra cứu combo cụ thể (2–5 tướng)" selected={selectedHeroes}
          excluded={[]} max={5} onChange={setSelectedHeroes} />
        {selectedCombo && <div className="method-banner">{("found" in selectedCombo && !selectedCombo.found)
          ? "Combo này chưa xuất hiện trong tập train."
          : `${selectedCombo.matches} lần quan sát · ${selectedCombo.wins} thắng · ${percent(selectedCombo.win_rate)} tỷ lệ quan sát`}</div>}
        <div className="table-wrap"><table><thead><tr><th>Nhóm tướng</th><th>Trận</th><th>Thắng</th><th>Tỷ lệ quan sát</th></tr></thead>
        <tbody>{compositions.slice(0, 60).map((row, index) => <tr key={index}>
          <td>{row.heroes.join(" · ")}</td><td>{row.matches}</td><td>{row.wins}</td>
          <td><span className="table-tag">{percent(row.win_rate)}</span></td></tr>)}</tbody></table></div>
        {compositions.length === 0 && <p className="empty-hint">Không có combo thỏa điều kiện lọc.</p>}
        <p className="small muted">Tỷ lệ thắng quan sát có thể rất biến động khi số trận nhỏ.</p></div>}
      {tab === "compare" && (comparison ? <div className="compare-grid">{["apriori", "fpgrowth"].map(key =>
        <div className="compare-card" key={key}><span className="eyebrow">{key.toUpperCase()}</span>
          <strong>{comparison[key].frequent_itemsets_count}</strong><span>tập phổ biến</span>
          <p>{comparison[key].total_rules_count} luật · {comparison[key].execution_time_sec.toFixed(3)} giây</p></div>)}
        <p className="muted small">Cùng bộ dữ liệu và ngưỡng; {comparison.common_compositions} combo chung.</p></div>
        : <div className="empty-state"><Layers3 size={36} /><h3>Chưa có so sánh</h3><p>Nhấn “So sánh hai thuật toán” để bắt đầu.</p></div>)}
    </div></div>
  </>;
}

function Draft({ heroes }: { heroes: Hero[] }) {
  const [own, setOwn] = useState<string[]>([]);
  const [enemy, setEnemy] = useState<string[]>([]);
  const [banned, setBanned] = useState<string[]>([]);
  const [action, setAction] = useState<"pick" | "ban">("pick");
  const [result, setResult] = useState<DraftResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run() {
    setBusy(true); setError(""); setResult(null);
    try { setResult(await post("/draft/recommend", { action, own_picks: own, enemy_picks: enemy, banned, k: 5 })); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  return <>
    <Header eyebrow="02 / DRAFT ASSISTANT" title="Trợ lý cấm chọn"
      subtitle="Gợi ý dựa trên mẫu quan sát trong tập train — không phải lựa chọn tối ưu theo luật giải." />
    <div className="layout-two"><div className="panel control-panel">
      <h3><Swords size={19} /> Ngữ cảnh đội hình</h3>
      <div className="segmented"><button className={action === "pick" ? "active" : ""} onClick={() => { setAction("pick"); setResult(null); }}>Gợi ý chọn</button>
        <button className={action === "ban" ? "active" : ""} onClick={() => { setAction("ban"); setResult(null); }}>Gợi ý cấm</button></div>
      <HeroPicker heroes={heroes} label="Đội của bạn" selected={own} excluded={[...enemy, ...banned]}
        max={action === "pick" ? 4 : 5} onChange={ids => { setOwn(ids); setResult(null); }} />
      <HeroPicker heroes={heroes} label="Đội đối thủ" selected={enemy} excluded={[...own, ...banned]} max={5}
        onChange={ids => { setEnemy(ids); setResult(null); }} />
      <HeroPicker heroes={heroes} label="Tướng đã cấm / bị khóa" selected={banned} excluded={[...own, ...enemy]} max={heroes.length}
        onChange={ids => { setBanned(ids); setResult(null); }} />
      <button className="btn primary full" disabled={busy || !heroes.length} onClick={run}>{busy ? "Đang tính..." : `Xem gợi ý ${action === "pick" ? "chọn" : "cấm"}`} <Sparkles size={17} /></button>
    </div><div className="panel result-panel">
      <div className="panel-title"><div><span className="eyebrow">TỪ DỮ LIỆU TRAIN</span><h2>Gợi ý dành cho bạn</h2></div><span className="status-pill">TOP 5</span></div>
      {error && <p role="alert" className="error">{error}</p>}
      {result ? <>
        <div className="method-banner"><CircleHelp size={18} /><span>{result.action === "pick"
          ? "Xếp hạng theo tương đồng cosine với đồng đội. Đối thủ chỉ được dùng để loại trừ tướng."
          : "Xếp hạng theo tần suất bị cấm trong các trận train, không đo mức khắc chế."}</span></div>
        <div className="recommendations">{result.recommendations.map(row =>
          <div className="recommendation" key={row.hero_id}><span className="rank">#{row.rank}</span>
            <span className="hero-avatar">{row.hero_name.slice(0, 1)}</span>
            <div className="rec-main"><strong>{row.hero_name}</strong><small>{result.action === "pick"
              ? `Xuất hiện ${row.evidence.train_lineup_count ?? 0} lần trong train`
              : `Bị cấm ${row.evidence.train_ban_count ?? 0} / ${row.evidence.train_games ?? "?"} trận train`}</small></div>
            <span className="rec-score">{result.action === "pick" ? row.score.toFixed(3) : percent(row.score)}<small>điểm quan sát</small></span>
          </div>)}</div>
        {result.returned_count === 0 && <p className="empty-hint">Không còn ứng viên phù hợp trong model train.</p>}
        {result.popularity_tiebreak_for_all_zero_scores && <p className="small muted">Mọi điểm cosine bằng 0: thứ tự được phá hòa theo tần suất train.</p>}
      </> : <div className="empty-state"><Sparkles size={36} /><h3>Đang chờ đội hình</h3><p>Chọn những tướng đã biết rồi yêu cầu một gợi ý.</p></div>}
      <div className="footnote"><ShieldAlert size={17} /><span>Điểm gợi ý không phải xác suất thắng. Chất lượng ở lượt draft live chưa được đánh giá.</span></div>
    </div></div>
  </>;
}

function Prediction({ heroes, patches }: { heroes: Hero[]; patches: string[] }) {
  const [teamA, setTeamA] = useState<string[]>([]);
  const [teamB, setTeamB] = useState<string[]>([]);
  const [side, setSide] = useState<"blue" | "red">("blue");
  const [patch, setPatch] = useState("");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (patches.length && !patch) setPatch(patches[patches.length - 1]); }, [patches, patch]);
  async function run() {
    setBusy(true); setError(""); setResult(null);
    try { setResult(await post("/predictions/win", {
      team_a_heroes: teamA, team_b_heroes: teamB, team_a_side: side, patch_id: patch,
    })); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  return <>
    <Header eyebrow="03 / MATCH PREDICTION" title="Sau khi chọn tướng"
      subtitle="Thử nghiệm dự đoán sau draft; cần đầy đủ 5 tướng mỗi đội, phe và patch." />
    <div className="warning"><ShieldAlert size={21} /><span><strong>Demo nghiên cứu:</strong> mô hình dự đoán không vượt baseline trên tập test. Xác suất không bảo đảm kết quả trận thực tế.</span></div>
    <div className="layout-two"><div className="panel control-panel">
      <h3><Target size={19} /> Thiết lập trận đấu</h3>
      <HeroPicker heroes={heroes} label="Đội A" selected={teamA} excluded={teamB} max={5} onChange={ids => { setTeamA(ids); setResult(null); }} />
      <HeroPicker heroes={heroes} label="Đội B" selected={teamB} excluded={teamA} max={5} onChange={ids => { setTeamB(ids); setResult(null); }} />
      <label>Phe của đội A <select value={side} onChange={e => { setSide(e.target.value as typeof side); setResult(null); }}><option value="blue">Xanh (Blue)</option><option value="red">Đỏ (Red)</option></select></label>
      <label>Phiên bản patch <select value={patch} onChange={e => { setPatch(e.target.value); setResult(null); }}>
        {patches.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <button className="btn primary full" disabled={busy || teamA.length !== 5 || teamB.length !== 5 || !patch}
        onClick={run}>{busy ? "Đang tính..." : "Xem kết quả thử nghiệm"} <ArrowRight size={17} /></button>
      <p className="small muted">Chỉ dùng tướng, phe và patch. Không dùng nhãn hay thống kê sau trận làm đầu vào.</p>
    </div><div className="panel result-panel">
      <div className="panel-title"><div><span className="eyebrow">RESEARCH MODEL</span><h2>Phân tích trận đấu</h2></div><span className="status-pill">POST-DRAFT</span></div>
      {error && <p role="alert" className="error">{error}</p>}
      {result ? <div className="prediction-output">
        <p className="muted">Xác suất ước lượng đội A thắng</p><strong className="big-number">{percent(result.team_a_win_probability)}</strong>
        <div className="probability-bar"><span style={{ width: `${result.team_a_win_probability * 100}%` }} /></div>
        <div className="probability-labels"><span>ĐỘI A</span><span>ĐỘI B · {percent(1 - result.team_a_win_probability)}</span></div>
        <div className="baseline-box"><span>Baseline chỉ theo phe</span><strong>{percent(result.side_baseline_probability)}</strong></div>
        <p className="small muted">Mô hình: {result.model_version}. {result.limitations}</p>
        {(result.unknown_categories.team_a_heroes.length > 0 || result.unknown_categories.team_b_heroes.length > 0
          || result.unknown_categories.patch_id) && <p className="warning small">Có tướng hoặc patch chưa xuất hiện trong train; kết quả càng không chắc chắn.</p>}
      </div> : <div className="empty-state"><Activity size={36} /><h3>Chưa đủ dữ kiện</h3><p>Hoàn thiện hai đội hình để xem kết quả thử nghiệm.</p></div>}
    </div></div>
  </>;
}

function About({ overview }: { overview: Overview | null }) {
  return <>
    <Header eyebrow="METHODOLOGY" title="Về dữ liệu & phương pháp"
      subtitle="Biết mô hình đã học gì quan trọng không kém việc xem kết quả." />
    <div className="about-grid">
      <div className="panel about-card"><span className="eyebrow">01 / DATASET</span><h2>Một giải đấu, một snapshot</h2>
        <p>Dữ liệu Đấu Trường Danh Vọng mùa xuân 2026. Tập train gồm 231 ván; 28 ván validation và 40 ván test được giữ riêng theo series. Kết quả không đại diện cho mọi rank, mùa giải hoặc patch.</p>
        <code>Snapshot {overview?.dataset_version.slice(0, 16) || "035ce761e53a47db"}…</code></div>
      <div className="panel about-card"><span className="eyebrow">02 / ASSOCIATION</span><h2>Luật không phải nguyên nhân</h2>
        <p>Apriori và FP-Growth tìm tập tướng thường gặp và luật kết hợp với thắng/thua. Support tính trên transaction đội; confidence/lift mô tả dữ liệu quan sát, không chứng minh combo gây ra chiến thắng.</p></div>
      <div className="panel about-card"><span className="eyebrow">03 / DRAFT</span><h2>Gợi ý, không tối ưu</h2>
        <p>Gợi ý pick dùng cosine đồng đội, ban dùng tần suất ban train. Điểm không phải xác suất thắng; model chưa được đánh giá trên test độc lập V2 hoặc thứ tự draft live. Backend không kiểm tra luật giải đấu.</p></div>
      <div className="panel about-card"><span className="eyebrow">04 / PREDICTION</span><h2>Trung thực với baseline</h2>
        <p>Random Forest depth 3 chỉ fit trên train. Test Brier 0.235367, kém baseline theo phe 0.233249; balanced accuracy 0.4815. Chức năng này là demo nghiên cứu, không phải khuyến nghị đặt cược hoặc cam kết thắng.</p></div>
    </div>
    <div className="notice"><ShieldAlert size={21} /><p>Quyền phân phối dataset chưa được xác minh. Chỉ vận hành demo nội bộ/cục bộ cho đến khi có xác nhận về quyền sử dụng và phát hành công khai.</p></div>
  </>;
}

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [patches, setPatches] = useState<string[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    Promise.all([
      api<Overview>("/overview"), api<Hero[]>("/catalog/heroes"), api<string[]>("/catalog/patches"),
    ]).then(([summary, catalog, patchList]) => { setOverview(summary); setHeroes(catalog); setPatches(patchList); })
      .catch(error => setLoadError(`Không kết nối được backend: ${error.message}`));
  }, []);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  function go(next: Page) { setPage(next); setMobileMenu(false); window.scrollTo({ top: 0, behavior: "smooth" }); }
  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? "open" : ""}`}>
      <button className="brand" onClick={() => go("home")}><img className="brand-mark" src={brandMark} alt="" /><span>liqily<small>ARENA INTELLIGENCE</small></span></button>
      <span className="nav-label">KHÔNG GIAN LÀM VIỆC</span>
      <nav>{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => go(item.id)}>
        <item.icon size={19} strokeWidth={1.8} />{item.title}{page === item.id && <span className="active-indicator" />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><span className="note-icon"><FlaskConical size={19} /></span>
        <strong>Dữ liệu nghiên cứu</strong><p>Phân tích giải đấu chuyên nghiệp, không bảo đảm kết quả thực chiến.</p></div>
        <span className="version">LIQILY / RESEARCH PREVIEW</span></div>
    </aside>
    {mobileMenu && <button className="mobile-overlay" onClick={() => setMobileMenu(false)} aria-label="Đóng menu" />}
    <div className="main-column">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Mở menu"><Menu size={22} /></button>
        <span className="breadcrumb">LIQILY <ChevronRight size={14} /> {nav.find(item => item.id === page)?.title}</span></div>
        <div className="topbar-right"><span className="data-badge"><span className="pulse" /> DATASET 2026</span>
          <button className="icon-button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Đổi giao diện sáng/tối">{theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}</button></div></header>
      <main className="content">{loadError && <p role="alert" className="error">{loadError}</p>}
        {page === "home" && <Home overview={overview} go={go} />}
        {page === "mining" && <Mining heroes={heroes} />}
        {page === "draft" && <Draft heroes={heroes} />}
        {page === "prediction" && <Prediction heroes={heroes} patches={patches} />}
        {page === "about" && <About overview={overview} />}
      </main><footer>LIQILY · DỮ LIỆU ĐỂ KHÁM PHÁ, KHÔNG PHẢI LỜI HỨA CHIẾN THẮNG.</footer>
    </div>
  </div>;
}
