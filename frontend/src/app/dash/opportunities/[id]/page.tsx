export default async function OpportunityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">商机详情</h1>
      <p className="text-muted-foreground mt-1">商机 ID: {id}</p>
    </div>
  );
}
