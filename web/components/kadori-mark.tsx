import { cn } from '@/lib/utils';

const SIZE = { sm: 20, md: 24, lg: 32 } as const;

/** Navbar·파비콘 공통. 검정 배경, 위 보라·아래 흰, 가운데 흰 버튼+검정 C */
export function KadoriMark({
  className,
  size = 'md',
}: {
  className?: string;
  size?: keyof typeof SIZE;
}) {
  const px = SIZE[size];

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={px}
      height={px}
      role="img"
      aria-label="카도리"
      className={cn('shrink-0', className)}
    >
      <rect width="64" height="64" rx="14" fill="#000000" />
      <circle cx="32" cy="32" r="26" fill="#FFFFFF" />
      <path d="M6 32A26 26 0 0 1 58 32Z" fill="#7C3AED" />
      <path
        d="M40 13c4 2.4 6.2 6 4.6 9.2"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="2.4"
        strokeLinecap="round"
        opacity="0.8"
      />
      <path
        d="M47 17c2.4 2.2 3.4 4.6 2 6.8"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="1.4"
        strokeLinecap="round"
        opacity="0.5"
      />
      <rect x="4" y="29" width="56" height="6" fill="#000000" />
      <circle cx="32" cy="32" r="12.5" fill="#000000" />
      <circle cx="32" cy="32" r="8.6" fill="#FFFFFF" />
      <path fill="#000000" d="M36.2 27A6.5 6.5 0 1 0 36.2 37L34.3 34.8A3.6 3.6 0 1 1 34.3 29.2Z" />
    </svg>
  );
}
