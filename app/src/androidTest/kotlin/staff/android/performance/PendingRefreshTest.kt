package staff.android.performance

import android.graphics.Bitmap
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test

class PendingRefreshTest {
    private fun all(root: View): List<TextView> =
        (if (root is TextView) listOf(root) else emptyList()) +
            if (root is ViewGroup) (0 until root.childCount).flatMap { all(root.getChildAt(it)) } else emptyList()
    @Test fun savesCameraWhileSourceIsStillPending() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                all(activity.window.decorView).single { it.text.toString() == "Refresh collection" }.performClick()
            }
            val deadline = System.nanoTime() + 5_000_000_000L
            var pending = false
            while (!pending && System.nanoTime() < deadline) {
                scenario.onActivity { activity -> pending = all(activity.window.decorView).any { it.text.toString() == "Refreshing collection…" } }
                if (!pending) Thread.sleep(5)
            }
            assertTrue("The selected source must still be pending", pending)
            scenario.onActivity { activity ->
                fun texts() = all(activity.window.decorView)
                assertTrue(texts().any { it.text.toString() == "Refreshing collection…" })
                texts().single { it.text.toString() == "Save Camera" }.performClick()
                assertTrue(texts().any { it.text.toString() == "Saved Camera" })
                assertTrue("Saving must not complete refresh", texts().any { it.text.toString() == "Refreshing collection…" })
            }
            // Pixel capture is supplementary: review its rendered state separately.
            val instrumentation = InstrumentationRegistry.getInstrumentation()
            instrumentation.uiAutomation.takeScreenshot()?.let { bitmap ->
                instrumentation.targetContext.openFileOutput("pending-refresh.png", 0).use {
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
                }
                bitmap.recycle()
            }
            var completed = false
            while (!completed && System.nanoTime() < deadline) {
                scenario.onActivity { activity -> completed = all(activity.window.decorView).any { it.text.toString() == "Collection refreshed" } }
                if (!completed) Thread.sleep(10)
            }
            assertTrue("Refresh must complete", completed)
            scenario.onActivity { activity ->
                assertTrue(all(activity.window.decorView).any { it.text.toString() == "Saved Camera" })
                assertTrue(all(activity.window.decorView).any { it.text.toString() == "Tea" })
            }
        }
    }
}
