import CollapsibleCard from '../CollapsibleCard'

interface SettingCardProps {
  id: string
  title: string
  isCollapsed: boolean
  onToggle: (id: string) => void
  className?: string
  children: React.ReactNode
}

export default function SettingCard({
  id,
  title,
  isCollapsed,
  onToggle,
  className = 'settings-card',
  children,
}: SettingCardProps) {
  return (
    <CollapsibleCard
      id={id}
      title={title}
      isCollapsed={isCollapsed}
      onToggle={onToggle}
      className={className}
    >
      {children}
    </CollapsibleCard>
  )
}
