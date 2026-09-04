export type Assignment = {
  assignment_id: string
  assignment_number: string
  assignment_name: string
  created_at: string
}

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  })

  const body = await response.json()

  if (!response.ok) {
    if (response.status === 404) {
      return null as T
    }

    const error = new Error(
      body.detail || `API request failed: ${response.status}`,
    )
    ;(error as Error & { status?: number }).status = response.status
    throw error
  }

  return body as T
}

export async function getAssignment(
  assignmentNumber: string,
): Promise<Assignment | null> {
  try {
    return await request<Assignment>(
      `/api/v1/assignments/${encodeURIComponent(assignmentNumber)}`,
    )
  } catch (error) {
    const status =
      error instanceof Error
        ? (error as Error & { status?: number }).status
        : undefined

    if (status === 404) {
      return null
    }

    throw error
  }
}

export function createAssignment(
  assignmentNumber: string,
  assignmentName: string,
): Promise<Assignment> {
  return request<Assignment>('/api/v1/assignments', {
    method: 'POST',
    body: JSON.stringify({
      assignment_number: assignmentNumber,
      assignment_name: assignmentName,
    }),
  })
}
