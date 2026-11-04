import SportPicker from "../components/SportPicker";

export default function Matches() {
  return (
    <section>
      <h1 className="mb-2 text-2xl font-extrabold">매치</h1>
      <p className="mb-4 text-sm text-muted">종목을 골라 매치를 찾아보세요.</p>
      <SportPicker />
      <p className="mt-6 rounded-xl border border-edge bg-white p-5 text-sm text-muted">전체 매치 목록이 여기에 표시됩니다. (준비 중)</p>
    </section>
  );
}
