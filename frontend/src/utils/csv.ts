export function parseCsvLine(line: string): string[] {
  const values: string[] = []
  let current = ''
  let insideQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]

    if (char === '"') {
      if (insideQuotes && line[index + 1] === '"') {
        current += '"'
        index += 1
      } else {
        insideQuotes = !insideQuotes
      }
    } else if (char === ',' && !insideQuotes) {
      values.push(current.trim())
      current = ''
    } else {
      current += char
    }
  }

  values.push(current.trim())

  return values
}

export function convertCsvValue(value: string): unknown {
  const trimmed = value.trim()

  if (trimmed === '') {
    return null
  }

  if (trimmed.toLowerCase() === 'true') {
    return true
  }

  if (trimmed.toLowerCase() === 'false') {
    return false
  }

  const numeric = Number(trimmed)

  if (!Number.isNaN(numeric)) {
    return numeric
  }

  return trimmed
}

export function parseCsv(
  csvText: string,
  requiredColumns: string[],
): Record<string, unknown>[] {
  const lines = csvText
    .replace(/^\uFEFF/, '')
    .split(/\r?\n/)
    .filter((line) => line.trim() !== '')

  if (lines.length < 2) {
    throw new Error(
      'CSV must contain a header and at least one data row.',
    )
  }

  const headers = parseCsvLine(lines[0])

  const missingColumns = requiredColumns.filter(
    (column) => !headers.includes(column),
  )

  if (missingColumns.length > 0) {
    throw new Error(
      `CSV is missing required columns: ${missingColumns.join(', ')}`,
    )
  }

  const rows = lines.slice(1).map((line) => {
    const values = parseCsvLine(line)
    const row: Record<string, unknown> = {}

    headers.forEach((header, index) => {
      row[header] = convertCsvValue(values[index] ?? '')
    })

    return row
  })

  return rows.map((row) => {
    const cleaned: Record<string, unknown> = {}

    requiredColumns.forEach((column) => {
      cleaned[column] = row[column]
    })

    return cleaned
  })
}
