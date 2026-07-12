"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, FileText, Users, Calendar, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dash/opportunities", label: "商机管理", icon: FileText },
  { href: "/dash/review", label: "审核", icon: Users },
  { href: "/dash/projects", label: "项目管理", icon: Home },
  { href: "/dash/schedule", label: "排期", icon: Calendar },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r bg-card min-h-screen p-4">
      <div className="mb-8">
        <h1 className="text-xl font-bold">商机管理系统</h1>
      </div>
      <nav className="space-y-2">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              pathname === item.href || pathname.startsWith(item.href + "/")
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            )}>
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
