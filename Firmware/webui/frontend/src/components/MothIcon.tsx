export interface MothIconProps {
  className?: string
  size?: number
}

/**
 * MothIcon Component
 *
 * A simple moth/bug SVG icon used as a fallback when photo thumbnails fail to load.
 * Designed to be thematically appropriate for the Mothbox insect photography system.
 */
export default function MothIcon({ className = '', size = 200 }: MothIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 200 200"
      className={className}
      role="img"
      aria-label="Photo unavailable - moth icon"
    >
      {/* Background */}
      <rect fill="#e5e7eb" width="200" height="200" />

      {/* Moth illustration */}
      <g transform="translate(100, 100)">
        {/* Left wing */}
        <ellipse
          cx="-35"
          cy="0"
          rx="30"
          ry="40"
          fill="#9ca3af"
          opacity="0.7"
          transform="rotate(-15 -35 0)"
        />

        {/* Right wing */}
        <ellipse
          cx="35"
          cy="0"
          rx="30"
          ry="40"
          fill="#9ca3af"
          opacity="0.7"
          transform="rotate(15 35 0)"
        />

        {/* Wing spots (left) */}
        <circle cx="-35" cy="-5" r="6" fill="#6b7280" opacity="0.5" />
        <circle cx="-35" cy="8" r="4" fill="#6b7280" opacity="0.5" />

        {/* Wing spots (right) */}
        <circle cx="35" cy="-5" r="6" fill="#6b7280" opacity="0.5" />
        <circle cx="35" cy="8" r="4" fill="#6b7280" opacity="0.5" />

        {/* Body */}
        <ellipse cx="0" cy="0" rx="8" ry="25" fill="#6b7280" />

        {/* Head */}
        <circle cx="0" cy="-22" r="6" fill="#6b7280" />

        {/* Left antenna */}
        <path
          d="M -2,-26 Q -8,-35 -10,-42"
          stroke="#6b7280"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
        />

        {/* Right antenna */}
        <path
          d="M 2,-26 Q 8,-35 10,-42"
          stroke="#6b7280"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
        />
      </g>

      {/* Text label */}
      <text
        x="50%"
        y="85%"
        textAnchor="middle"
        fill="#6b7280"
        fontSize="12"
        fontFamily="system-ui, -apple-system, sans-serif"
      >
        Image Unavailable
      </text>
    </svg>
  )
}
