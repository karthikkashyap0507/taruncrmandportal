import { Skeleton } from "@/components/ui/skeleton";

export function PageSkeleton() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse px-4 py-12 sm:px-6 lg:px-8">
      <Skeleton className="mb-4 h-8 w-48 rounded-lg" />
      <Skeleton className="mb-2 h-12 w-full max-w-2xl rounded-lg" />
      <Skeleton className="mb-10 h-5 w-full max-w-xl rounded-lg" />
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}
