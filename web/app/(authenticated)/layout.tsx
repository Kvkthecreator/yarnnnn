import AuthenticatedLayout from "@/components/shell/AuthenticatedLayout";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <AuthenticatedLayout>{children}</AuthenticatedLayout>;
}
