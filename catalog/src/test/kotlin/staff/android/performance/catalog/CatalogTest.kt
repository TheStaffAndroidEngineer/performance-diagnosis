package staff.android.performance.catalog

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*

class CatalogTest {
    private val seed = listOf(Product("tea", "Tea", 45000))
    @Test fun broadLockMakesReaderWaitForSource() {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val pool = Executors.newFixedThreadPool(2)
        val catalog = BroadLockCatalog(seed, CatalogSource {
            entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); seed
        })
        try {
            val writer = pool.submit { catalog.refresh() }
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            val readerThread = AtomicReference<Thread>()
            val reader = pool.submit<CatalogSnapshot> { readerThread.set(Thread.currentThread()); catalog.snapshot() }
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
            while (readerThread.get()?.state != Thread.State.BLOCKED && System.nanoTime() < deadline) Thread.sleep(1)
            assertEquals(Thread.State.BLOCKED, readerThread.get()?.state)
            assertTrue(readerThread.get().stackTrace.any { it.className.endsWith("BroadLockCatalog") && it.methodName == "snapshot" })
            assertFalse(reader.isDone)
            release.countDown(); writer.get(5, TimeUnit.SECONDS)
            assertEquals(1L, reader.get(5, TimeUnit.SECONDS).revision)
        } finally { release.countDown(); pool.shutdownNow() }
    }
    @Test fun snapshotRemainsAvailableDuringUncompletedSource() {
        val catalog = SnapshotCatalog(seed)
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        val pool = Executors.newSingleThreadExecutor()
        try {
            val ticket = catalog.beginRefresh()
            val pending = pool.submit { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); catalog.publish(ticket, seed) }
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            assertEquals(CatalogSnapshot(0, seed), catalog.snapshot())
            release.countDown(); pending.get(5, TimeUnit.SECONDS)
            assertEquals(1L, catalog.snapshot().revision)
        } finally { release.countDown(); pool.shutdownNow() }
    }
    @Test fun laterAdmissionRevokesEarlierPublishEvenBeforeLaterSuccess() {
        val catalog = SnapshotCatalog(seed)
        val old = catalog.beginRefresh(); val current = catalog.beginRefresh()
        assertFalse(catalog.publish(old, listOf(Product("old", "Old", 1))))
        assertEquals(0L, catalog.snapshot().revision)
        assertTrue(catalog.publish(current, seed)); assertEquals(1L, catalog.snapshot().revision)
    }
    @Test fun oldCompletionCannotReplaceAcceptedNewerResult() {
        val catalog = SnapshotCatalog(seed);val before = catalog.snapshot()
        val old = catalog.beginRefresh();val newer = catalog.beginRefresh()
        val newProducts = listOf(Product("tea", "Tea new", 45000))
        assertTrue(catalog.publish(newer, newProducts))
        assertFalse(catalog.publish(old, seed))
        assertEquals(CatalogSnapshot(1, newProducts), catalog.snapshot())
        assertEquals(CatalogSnapshot(0, seed), before)
    }
    @Test fun rejectsInvalidBatchWithoutChangingAcceptedState() {
        val catalog = SnapshotCatalog(seed);val ticket = catalog.beginRefresh()
        assertThrows(IllegalArgumentException::class.java) { catalog.publish(ticket, listOf(Product("tea", "Tea", -1))) }
        assertEquals(CatalogSnapshot(0, seed), catalog.snapshot())
    }
    @Test fun freezesCallerContainerAndRejectsMutationThroughSnapshot() {
        val source = seed.toMutableList(); val catalog = SnapshotCatalog(source); source.clear()
        assertEquals(1, catalog.snapshot().products.size)
        assertThrows(UnsupportedOperationException::class.java) { (catalog.snapshot().products as MutableList).clear() }
    }
    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun ownerRetainsAcceptedDataAfterFailure() = runTest {
        val catalog = SnapshotCatalog(seed)
        val owner = RefreshOwner(catalog, CatalogSource { error("controlled") }, this, StandardTestDispatcher(testScheduler))
        owner.refresh(); assertTrue(owner.state.value.refreshing); advanceUntilIdle()
        assertFalse(owner.state.value.refreshing); assertTrue(owner.state.value.message.startsWith("Refresh unavailable"))
        assertEquals(CatalogSnapshot(0, seed), catalog.snapshot())
    }
    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun cancelledOwnerDoesNotPublish() = runTest {
        val catalog = SnapshotCatalog(seed); val dispatcher = StandardTestDispatcher(testScheduler)
        val child = CoroutineScope(SupervisorJob() + dispatcher)
        val owner = RefreshOwner(catalog, CatalogSource { seed }, child, dispatcher)
        owner.refresh(); child.cancel(); advanceUntilIdle()
        assertEquals(0L, catalog.snapshot().revision)
    }
    @Test fun cancellationDuringSourcePreventsPublication() = runBlocking {
        val catalog = SnapshotCatalog(seed)
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        val io = Executors.newSingleThreadExecutor().asCoroutineDispatcher()
        try {
            val owner = RefreshOwner(catalog, CatalogSource {
                entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); seed
            }, this, io)
            val job = owner.refresh(); yield()
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            job.cancel(); release.countDown(); job.join()
            assertEquals(0L, catalog.snapshot().revision)
        } finally { release.countDown(); io.close() }
    }
    @Test fun cpuWorkHasObservableDeterministicOutput() {
        assertEquals(CpuWork.checksum(1000), CpuWork.checksum(1000))
        assertNotEquals(CpuWork.checksum(999), CpuWork.checksum(1000))
    }
}
