const days = ["일", "월", "화", "수", "목", "금", "토"];

// "11/12(목) 19:00" 형태. 사용자의 브라우저 시간대로 보여준다
export function formatWhen(iso: string): string {
  const d = new Date(iso);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]}) ${hh}:${mm}`;
}
