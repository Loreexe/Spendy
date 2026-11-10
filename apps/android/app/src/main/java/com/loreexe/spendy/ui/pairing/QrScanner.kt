package com.loreexe.spendy.ui.pairing

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.zxing.BinaryBitmap
import com.google.zxing.NotFoundException
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import com.google.zxing.qrcode.QRCodeReader
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Scanner QR minimale basato su CameraX + ZXing core.
 * Decodifica i frame della fotocamera posteriore e restituisce il primo payload valido.
 */
@Composable
fun QrScannerScreen(
    onScanned: (String) -> Unit,
    onClose: () -> Unit,
) {
    val context = LocalContext.current
    var granted by remember { mutableStateOf(hasCameraPermission(context)) }
    var error by remember { mutableStateOf<String?>(null) }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { result -> granted = result }

    LaunchedEffect(Unit) {
        if (!granted) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    Box(modifier = Modifier.fillMaxSize().background(Color.Black)) {
        if (granted) {
            CameraPreview(
                onScanned = onScanned,
                onError = { message -> error = message },
            )
        }
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(16.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            TextButton(onClick = onClose) {
                Text("Chiudi", color = Color.White)
            }
            Column(
                modifier = Modifier.fillMaxWidth().padding(bottom = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (!granted) {
                    Text(
                        "Serve il permesso per usare la fotocamera.",
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Button(onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) }) {
                        Text("Consenti fotocamera")
                    }
                } else {
                    Text(
                        "Inquadra il QR di Spendy",
                        color = Color.White,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                error?.let {
                    Text(
                        it,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun CameraPreview(
    onScanned: (String) -> Unit,
    onError: (String) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val currentOnScanned by rememberUpdatedState(onScanned)
    val previewView = remember {
        PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER }
    }
    val mainExecutor = remember { ContextCompat.getMainExecutor(context) }

    DisposableEffect(Unit) {
        val executor = Executors.newSingleThreadExecutor()
        val done = AtomicBoolean(false)
        val providerFuture = ProcessCameraProvider.getInstance(context)
        val listener = Runnable {
            try {
                val provider = providerFuture.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                analysis.setAnalyzer(executor) { image ->
                    if (!done.get()) {
                        val payload = runCatching { decodeQr(image) }.getOrNull()
                        if (payload != null && done.compareAndSet(false, true)) {
                            mainExecutor.execute { currentOnScanned(payload) }
                        }
                    }
                    image.close()
                }
                provider.unbindAll()
                provider.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    analysis,
                )
            } catch (throwable: Throwable) {
                mainExecutor.execute {
                    onError(throwable.message ?: "Fotocamera non disponibile.")
                }
            }
        }
        providerFuture.addListener(listener, mainExecutor)
        onDispose {
            analysisShutdown(providerFuture, executor)
        }
    }

    AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())
}

private fun analysisShutdown(
    providerFuture: com.google.common.util.concurrent.ListenableFuture<ProcessCameraProvider>,
    executor: java.util.concurrent.ExecutorService,
) {
    runCatching { providerFuture.get().unbindAll() }
    executor.shutdown()
}

private fun hasCameraPermission(context: Context): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
        PackageManager.PERMISSION_GRANTED

private fun decodeQr(image: ImageProxy): String? {
    val plane = image.planes.firstOrNull() ?: return null
    val width = image.width
    val height = image.height
    if (width <= 0 || height <= 0) return null
    val buffer = plane.buffer
    buffer.rewind()
    val rowStride = plane.rowStride
    val data: ByteArray = if (rowStride == width) {
        ByteArray(buffer.remaining()).also { buffer.get(it) }
    } else {
        val raw = ByteArray(buffer.remaining()).also { buffer.get(it) }
        if (raw.size < rowStride * height) return null
        val cropped = ByteArray(width * height)
        for (row in 0 until height) {
            System.arraycopy(raw, row * rowStride, cropped, row * width, width)
        }
        cropped
    }
    if (data.size < width * height) return null
    val source = PlanarYUVLuminanceSource(data, width, height, 0, 0, width, height, false)
    val bitmap = BinaryBitmap(HybridBinarizer(source))
    return try {
        QRCodeReader().decode(bitmap).text
    } catch (notFound: NotFoundException) {
        null
    }
}
