package staff.android.performance

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.Assert.*

class ShopTest {
    private fun views(root: View): List<View> = listOf(root) +
        if (root is ViewGroup) (0 until root.childCount).flatMap { views(root.getChildAt(it)) } else emptyList()
    private fun text(activity: MainActivity, value: String): TextView = views(activity.window.decorView).filterIsInstance<TextView>().single { it.text.toString() == value }
    private fun waitFor(scenario: ActivityScenario<MainActivity>, value: String) {
        val end = System.nanoTime() + 8_000_000_000L
        var found = false
        while (!found && System.nanoTime() < end) {
            scenario.onActivity { found = views(it.window.decorView).filterIsInstance<TextView>().any { v -> v.text.toString() == value } }
            if (!found) Thread.sleep(25)
        }
        assertTrue("Missing completed state: $value", found)
    }
    private fun launch(mode: String? = null): ActivityScenario<MainActivity> {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val intent = Intent(context, MainActivity::class.java)
        if (mode != null) intent.putExtra("scenario", mode)
        return ActivityScenario.launch(intent)
    }
    @Test fun normalShopShowsProductsAndPreservesSavedChoiceAcrossRefresh() {
        launch().use { scenario ->
            scenario.onActivity { activity ->
                assertNotNull(text(activity,"Camera"));assertNotNull(text(activity,"Tea"))
                text(activity,"Save Camera").performClick()
                text(activity,"Refresh collection").performClick()
            }
            waitFor(scenario,"Collection refreshed")
            scenario.onActivity { assertNotNull(text(it,"Saved Camera"));assertNotNull(text(it,"Tea")) }
        }
    }
    @Test fun failedRefreshRetainsProductsAndRevision() {
        launch("failure").use { scenario ->
            waitFor(scenario,"Refresh unavailable. Your collection is still here.")
            scenario.onActivity { assertNotNull(text(it,"Camera"));assertNotNull(text(it,"Tea"));assertNotNull(text(it,"Accepted revision: 0")) }
        }
    }
    @Test fun repairedRefreshPublishesOneCompleteSnapshot() {
        launch("repaired").use { scenario ->
            waitFor(scenario,"Collection refreshed")
            scenario.onActivity { assertNotNull(text(it,"Accepted revision: 1"));assertNotNull(text(it,"Camera"));assertNotNull(text(it,"Tea")) }
        }
    }
    @Test fun diagnosticDisclosureDoesNotResetSavedChoice() {
        launch().use { scenario ->
            scenario.onActivity {
                text(it,"Save Camera").performClick();text(it,"Lab controls").performClick()
                text(it,"Close lab controls").performClick();assertNotNull(text(it,"Saved Camera"))
            }
        }
    }
}
