'use client'

import { useState, type FormEvent } from 'react'
import axios from 'axios'
import apiClient from '@/lib/api-client'
import { useUserRole } from '@/hooks/useUserRole'

interface ImportResult {
  rows_inserted: number
  items_matched: number
  orders_skipped: number
  validation_errors: { row: number; errors: string[] }[]
}

export default function ImportSalesPage() {
  const { canManage, loading } = useUserRole()
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setResult(null)
    if (!file || !file.name.toLowerCase().endsWith('.csv')) { setError('Choose a CSV file.'); return }
    if (file.size > 5 * 1024 * 1024) { setError('The CSV must be 5 MB or smaller.'); return }
    setBusy(true)
    setError('')
    const body = new FormData()
    body.append('file', file)
    try {
      const response = await apiClient.post<ImportResult>('/data/upload-sales', body, {
        headers: { 'Content-Type': undefined }, timeout: 60000,
      })
      setResult(response.data)
    } catch (failure: unknown) {
      const detail: unknown = axios.isAxiosError(failure) ? failure.response?.data?.detail : undefined
      setError(typeof detail === 'string' ? detail : 'Import failed. Please try again.')
    } finally { setBusy(false) }
  }

  if (loading) return <p className="p-8">Loading permissions…</p>
  if (!canManage) return <p className="p-8">Only managers and owners can import sales.</p>
  return <div className="p-8 overflow-auto space-y-6 max-w-4xl">
    <h1 className="text-2xl font-semibold">Import sales</h1>
    <p>Upload historical orders in INR. Use your existing menu item names and a stable order ID from your sales system.</p>
    <a className="text-accent underline" href="/sales-import-template.csv" download>Download CSV template</a>
    <div className="bg-surface border border-line rounded p-4 space-y-2 text-sm">
      <p>Required: order_id, date, item_name, quantity, unit_price, total_amount, payment_method, tax_amount. customer_id is optional.</p>
      <p>Repeat the order subtotal, tax, payment method, date and customer on each line. The subtotal must equal the sum of line prices × quantities. Tax is an INR amount, not a percentage.</p>
      <p>Up to 5 MB, 10,000 rows, 100 lines per order and 1,000 units per line. Dates are UTC. Save CSV as UTF-8.</p>
      <p>Exact retries are skipped. Reusing an order ID with different content is rejected. One invalid line rejects the whole order; other valid orders are imported.</p>
      <p>Replace the example item names before uploading. Older exports need the new columns; check for orders already imported before these retry safeguards were added.</p>
    </div>
    <form onSubmit={submit} className="space-y-4">
      <label className="block">Sales CSV<input className="block mt-2" type="file" accept=".csv,text/csv" disabled={busy}
        onChange={event => { setFile(event.target.files?.[0] ?? null); setError(''); setResult(null) }} /></label>
      <button disabled={busy || !file} className="bg-accent text-black px-4 py-2 rounded disabled:opacity-50">{busy ? 'Importing…' : 'Import sales'}</button>
    </form>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    {result && <section aria-live="polite" className="space-y-3">
      <h2 className="text-lg font-semibold">Import results</h2>
      <p>{result.rows_inserted} orders imported · {result.items_matched} lines matched · {result.orders_skipped} orders skipped</p>
      {result.validation_errors.length > 0 && <table className="w-full text-left"><thead><tr><th>Data row</th><th>Issue</th></tr></thead><tbody>
        {result.validation_errors.map((issue, index) => <tr key={`${issue.row}-${index}`}><td className="align-top pr-4">{issue.row}</td><td>{issue.errors.join('; ')}</td></tr>)}
      </tbody></table>}
    </section>}
  </div>
}
