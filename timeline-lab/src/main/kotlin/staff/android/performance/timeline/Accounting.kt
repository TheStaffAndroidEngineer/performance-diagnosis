package staff.android.performance.timeline

enum class TraceState { RUNNING, RUNNABLE, SLEEPING, UNINTERRUPTIBLE, UNKNOWN }
data class ThreadInterval(val thread: String, val startNanos: Long, val endNanos: Long, val state: TraceState)
data class TraceWindow(val startNanos: Long, val endNanos: Long)
data class TimeBudget(
    val runningNanos: Long, val runnableNanos: Long, val sleepingNanos: Long,
    val uninterruptibleNanos: Long, val unknownNanos: Long,
) {
    val totalNanos: Long get() = listOf(runningNanos, runnableNanos, sleepingNanos, uninterruptibleNanos, unknownNanos)
        .fold(0L) { total, value -> Math.addExact(total, value) }
}
object LearnerAccounting {
    fun account(window: TraceWindow, thread: String, intervals: List<ThreadInterval>): TimeBudget {
        // Deliberate starter: replace with the exercise contract.
        return TimeBudget(Math.subtractExact(window.endNanos, window.startNanos), 0, 0, 0, 0)
    }
}
object ReferenceAccounting {
    fun account(window: TraceWindow, thread: String, intervals: List<ThreadInterval>): TimeBudget {
        require(window.endNanos > window.startNanos)
        require(thread.isNotBlank())
        val length = Math.subtractExact(window.endNanos, window.startNanos)
        intervals.forEach { require(it.thread.isNotBlank() && it.endNanos > it.startNanos) }
        val selected = intervals.filter { it.thread == thread }
            .map { it.copy(startNanos = maxOf(it.startNanos, window.startNanos), endNanos = minOf(it.endNanos, window.endNanos)) }
            .filter { it.startNanos < it.endNanos }
            .sortedBy { it.startNanos }
        val totals = LongArray(TraceState.entries.size)
        var cursor = window.startNanos
        for (interval in selected) {
            require(interval.startNanos >= cursor) { "Overlapping target-thread intervals" }
            totals[TraceState.UNKNOWN.ordinal] = Math.addExact(totals[TraceState.UNKNOWN.ordinal], Math.subtractExact(interval.startNanos, cursor))
            val duration = Math.subtractExact(interval.endNanos, interval.startNanos)
            totals[interval.state.ordinal] = Math.addExact(totals[interval.state.ordinal], duration)
            cursor = interval.endNanos
        }
        totals[TraceState.UNKNOWN.ordinal] = Math.addExact(totals[TraceState.UNKNOWN.ordinal], Math.subtractExact(window.endNanos, cursor))
        return TimeBudget(totals[0], totals[1], totals[2], totals[3], totals[4]).also { check(it.totalNanos == length) }
    }
}
