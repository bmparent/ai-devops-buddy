export async function getMessage(): Promise<string> {
  const res = await fetch('/api/message');
  const data = await res.json();
  return data.message;
}
