import podiumLogo from '../../assets/podium-logo.png';

interface LogoProps {
  dark?: boolean;
  height?: number;
}

export function Logo({ dark = false, height = 135 }: LogoProps) {
  return (
    <img
      src={podiumLogo}
      alt="Podium"
      style={{
        height: `${height}px`,
        width: 'auto',
        objectFit: 'contain',
        display: 'block',
        ...(dark ? { filter: 'invert(1)', opacity: 0.5 } : {})
      }}
    />
  );
}
