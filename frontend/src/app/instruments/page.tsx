import { redirect } from 'next/navigation'

// The old Markets table read the retired engine's setup state. Every pair's live
// state is on the Bias Board's Live Chart Board, so old links land there.
export default function InstrumentsPage() {
  redirect('/dashboard')
}
