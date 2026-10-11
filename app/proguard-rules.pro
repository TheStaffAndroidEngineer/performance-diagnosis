# Keep diagnostic workload names available to the sampled-profile investigation.
# This local tracing variant uses the same rules for every measured comparison.
-keepnames class staff.android.performance.catalog.CpuWork { *; }
