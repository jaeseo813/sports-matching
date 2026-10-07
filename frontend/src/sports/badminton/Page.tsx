import { badminton } from ".";

// 배드민턴 담당 영역: 이 폴더(src/sports/badminton) 안에서만 작업한다.
export default function Page() {
  return (
    <section>
      <h1 className="text-2xl font-extrabold">{badminton.name}</h1>
      <p className="mt-2 rounded-xl border border-edge bg-white p-5 text-sm text-muted">
        배드민턴 화면이 여기에 들어갑니다. (준비 중)
      </p>
    </section>
  );
}
