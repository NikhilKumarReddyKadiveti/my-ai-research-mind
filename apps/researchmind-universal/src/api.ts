const apiUrl = process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function callApi<T>(path: string, token: string, body: unknown): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${apiUrl}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot reach ResearchMind API at ${apiUrl}. Start the backend server and try again.`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail ?? `Request failed with status ${response.status}`);
  }

  return data as T;
}
