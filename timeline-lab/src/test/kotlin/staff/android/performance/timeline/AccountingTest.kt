package staff.android.performance.timeline
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
class AccountingTest {
    private fun account(w: TraceWindow, t: String, rows: List<ThreadInterval>): TimeBudget =
        if (System.getProperty("timeline.solution") == "learner") LearnerAccounting.account(w, t, rows)
        else ReferenceAccounting.account(w, t, rows)
    private fun row(a: Long, b: Long, s: TraceState, t: String = "upload") = ThreadInterval(t, a, b, s)
    @Test fun clipsBothEndsAndKeepsMissingTime() {
        val result = account(TraceWindow(10,24),"upload",listOf(row(8,12,TraceState.RUNNING),row(12,15,TraceState.RUNNABLE),row(15,20,TraceState.SLEEPING),row(22,26,TraceState.RUNNING)))
        assertEquals(TimeBudget(4,3,5,0,2),result);assertEquals(14L,result.totalNanos)
    }
    @Test fun unsortedIntervalsHaveSameBudget() {
        assertEquals(TimeBudget(2,3,0,0,0),account(TraceWindow(0,5),"upload",listOf(row(2,5,TraceState.RUNNABLE),row(0,2,TraceState.RUNNING))))
    }
    @Test fun explicitUnknownAndGapsAreBothUnknown() {
        assertEquals(TimeBudget(0,0,0,0,10),account(TraceWindow(0,10),"upload",listOf(row(2,7,TraceState.UNKNOWN))))
    }
    @Test fun otherThreadsDoNotConsumeTargetBudget() {
        assertEquals(TimeBudget(5,0,0,0,0),account(TraceWindow(0,5),"upload",listOf(row(0,5,TraceState.RUNNING),row(0,5,TraceState.SLEEPING,"worker"))))
    }
    @Test fun overlappingTargetStatesAreRejected() {
        assertThrows(IllegalArgumentException::class.java) { account(TraceWindow(0,5),"upload",listOf(row(0,4,TraceState.RUNNING),row(3,5,TraceState.RUNNABLE))) }
    }
    @Test fun adjacencyIsNotOverlap() {
        assertEquals(TimeBudget(3,0,0,2,0),account(TraceWindow(0,5),"upload",listOf(row(0,3,TraceState.RUNNING),row(3,5,TraceState.UNINTERRUPTIBLE))))
    }
    @Test fun entirelyOutsideIntervalsDoNotOverlapInsideWindow() {
        assertEquals(TimeBudget(0,0,0,0,5),account(TraceWindow(10,15),"upload",listOf(row(0,8,TraceState.RUNNING),row(2,9,TraceState.SLEEPING),row(15,20,TraceState.RUNNING))))
    }
    @Test fun emptyDataIsMissingNotIdle() {
        assertEquals(TimeBudget(0,0,0,0,4),account(TraceWindow(4,8),"upload",emptyList()))
    }
    @Test fun zeroLengthWindowIsRejected() {
        assertThrows(IllegalArgumentException::class.java) { account(TraceWindow(1,1),"upload",emptyList()) }
    }
    @Test fun reversedWindowIsRejected() {
        assertThrows(IllegalArgumentException::class.java) { account(TraceWindow(2,1),"upload",emptyList()) }
    }
    @Test fun invalidOtherThreadRowStillRejectsMalformedInput() {
        assertThrows(IllegalArgumentException::class.java) { account(TraceWindow(0,5),"upload",listOf(row(3,3,TraceState.RUNNING,"worker"))) }
    }
    @Test fun blankThreadIsRejected() {
        assertThrows(IllegalArgumentException::class.java) { account(TraceWindow(0,5)," ",emptyList()) }
    }
    @Test fun arithmeticOverflowIsReported() {
        assertThrows(ArithmeticException::class.java) { account(TraceWindow(Long.MIN_VALUE,Long.MAX_VALUE),"upload",emptyList()) }
    }
    @Test fun negativeTimestampCoordinatesAreValid() {
        assertEquals(TimeBudget(2,0,0,0,3),account(TraceWindow(-3,2),"upload",listOf(row(-2,0,TraceState.RUNNING))))
    }
}
