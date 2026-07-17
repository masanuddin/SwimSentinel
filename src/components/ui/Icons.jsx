/**
 * Ikon inline SVG (stroke, 24x24 viewBox) tanpa library eksternal.
 * Pakai: <HomeIcon className="h-4 w-4" />
 */

function Svg({ children, className = 'h-4 w-4', ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export function HomeIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
      <path d="M10 21v-6h4v6" />
    </Svg>
  )
}

export function MapIcon(props) {
  return (
    <Svg {...props}>
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" />
      <path d="M9 4v14" />
      <path d="M15 6v14" />
    </Svg>
  )
}

export function WavesIcon(props) {
  return (
    <Svg {...props}>
      <path d="M2 7c1.7 0 1.7 1.5 3.3 1.5S7 7 8.7 7s1.6 1.5 3.3 1.5S13.6 7 15.3 7s1.7 1.5 3.4 1.5S20.3 7 22 7" />
      <path d="M2 12c1.7 0 1.7 1.5 3.3 1.5S7 12 8.7 12s1.6 1.5 3.3 1.5 1.6-1.5 3.3-1.5 1.7 1.5 3.4 1.5 1.6-1.5 3.3-1.5" />
      <path d="M2 17c1.7 0 1.7 1.5 3.3 1.5S7 17 8.7 17s1.6 1.5 3.3 1.5 1.6-1.5 3.3-1.5 1.7 1.5 3.4 1.5 1.6-1.5 3.3-1.5" />
    </Svg>
  )
}

export function ChartIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4 20h16" />
      <path d="M7 20V10" />
      <path d="M12 20V4" />
      <path d="M17 20v-8" />
    </Svg>
  )
}

export function UserIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5" />
    </Svg>
  )
}

export function ArrowRightIcon(props) {
  return (
    <Svg {...props}>
      <path d="M4 12h16" />
      <path d="m13 5 7 7-7 7" />
    </Svg>
  )
}

export function VolumeIcon(props) {
  return (
    <Svg {...props}>
      <path d="M11 5 6.5 8.5H3v7h3.5L11 19V5Z" />
      <path d="M15 9a4 4 0 0 1 0 6" />
      <path d="M17.5 6.5a8 8 0 0 1 0 11" />
    </Svg>
  )
}

export function VolumeMutedIcon(props) {
  return (
    <Svg {...props}>
      <path d="M11 5 6.5 8.5H3v7h3.5L11 19V5Z" />
      <path d="m15.5 9.5 5 5" />
      <path d="m20.5 9.5-5 5" />
    </Svg>
  )
}
