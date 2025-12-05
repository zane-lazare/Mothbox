import { useSelectionContext } from '../contexts/SelectionContext'

export default function useSelection() {
  const context = useSelectionContext()
  if (!context) {
    throw new Error('useSelection must be used within SelectionProvider')
  }
  return context
}
