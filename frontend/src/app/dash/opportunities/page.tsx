"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import Link from "next/link";
import type { Opportunity } from "@/types";

const statusMap: Record<number, { label: string; variant: any }> = {
  0: { label: "录入", variant: "secondary" },
  1: { label: "待审核", variant: "warning" },
  2: { label: "审核通过", variant: "default" },
  3: { label: "审核驳回", variant: "destructive" },
  4: { label: "团队组建", variant: "secondary" },
  5: { label: "需求确认", variant: "secondary" },
  6: { label: "方案制定", variant: "secondary" },
  7: { label: "已排期", variant: "default" },
  8: { label: "签约中", variant: "warning" },
  9: { label: "已闭环", variant: "default" },
};

const urgencyMap: Record<number, string> = {
  1: "🔴 高", 2: "🟡 中", 3: "🟢 低",
};

export default function OpportunitiesPage() {
  const [search, setSearch] = useState("");

  const { data: opportunities, isLoading } = useQuery({
    queryKey: ["opportunities", search],
    queryFn: async () => {
      const res = await api.get("/opportunities", { params: { search } });
      return res.data.data as Opportunity[];
    },
  });

  const isOverdue = (deadline: string | null) => {
    if (!deadline) return false;
    return new Date(deadline) < new Date();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">商机管理</h1>
          <p className="text-muted-foreground mt-1">管理客户走访商机，跟踪全流程状态</p>
        </div>
        <Link href="/dash/opportunities/new">
          <Button><Plus className="mr-2 h-4 w-4" />新建走访</Button>
        </Link>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="搜索商机编号、客户名称..." className="pl-10"
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Button variant="outline" size="icon"><Filter className="h-4 w-4" /></Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>商机编号</TableHead><TableHead>客户</TableHead><TableHead>状态</TableHead>
              <TableHead>紧急度</TableHead><TableHead>预估金额</TableHead><TableHead>当前节点</TableHead>
              <TableHead>截止时间</TableHead><TableHead>创建时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8">加载中...</TableCell></TableRow>
            ) : opportunities?.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8 text-muted-foreground">暂无商机数据</TableCell></TableRow>
            ) : (
              opportunities?.map((opp) => {
                const status = statusMap[opp.status];
                const overdue = isOverdue(opp.nodeDeadline);
                return (
                  <TableRow key={opp.id} className="cursor-pointer hover:bg-muted/50">
                    <TableCell className="font-medium">
                      <Link href={`/dash/opportunities/${opp.id}`} className="hover:underline">{opp.code}</Link>
                    </TableCell>
                    <TableCell>{opp.customerName}</TableCell>
                    <TableCell><Badge variant={status?.variant || "default"}>{status?.label}</Badge></TableCell>
                    <TableCell>{urgencyMap[opp.urgencyLevel]}</TableCell>
                    <TableCell>{opp.estimateAmount ? `¥${(opp.estimateAmount / 10000).toFixed(1)}万` : "-"}</TableCell>
                    <TableCell>{opp.currentNode || "-"}</TableCell>
                    <TableCell>
                      {opp.nodeDeadline && (
                        <span className={overdue ? "text-red-500 font-medium" : ""}>
                          {overdue ? "⚠️ " : ""}{new Date(opp.nodeDeadline).toLocaleDateString()}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>{new Date(opp.createdAt).toLocaleDateString()}</TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
