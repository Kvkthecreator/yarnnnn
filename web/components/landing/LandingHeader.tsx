import Link from "next/link";
import Image from "next/image";

export default function LandingHeader() {
  return (
    <header className="w-full py-4 px-6 flex justify-between items-center border-b border-border">
      <Link href="/" className="flex items-center gap-2">
        <Image
          src="/assets/logos/circleonly_yarnnn.png"
          alt="YARNNN"
          width={32}
          height={32}
        />
        <span className="text-xl font-brand">yarnnn</span>
      </Link>
      <nav className="flex items-center gap-6">
        <Link
          href="/about"
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          About
        </Link>
        <Link
          href="/auth/login"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          Sign In
        </Link>
      </nav>
    </header>
  );
}
