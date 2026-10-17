import java.util.Properties

plugins {
    id("com.android.application")
}

// arquivos temporários da compilação fora do OneDrive (a sincronização trava os arquivos e quebra o build)
layout.buildDirectory.set(file(System.getenv("LOCALAPPDATA") + "/AndroidBuild/out/app"))

// chave de assinatura (fica em android/chave; sem ela não dá para publicar atualizações do mesmo app)
val chave = Properties().apply {
    val f = rootProject.file("chave/chave.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "br.editorpdf.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "br.editorpdf.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 7
        versionName = "2.0"
    }

    signingConfigs {
        create("release") {
            if (chave.isNotEmpty()) {
                storeFile = rootProject.file("chave/" + chave.getProperty("arquivo"))
                storePassword = chave.getProperty("senha")
                keyAlias = chave.getProperty("apelido")
                keyPassword = chave.getProperty("senha")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // a página e o motor são copiados de Adobe\sistema pelo gerar-apk.ps1 para fora do OneDrive
    sourceSets.getByName("main").assets.directories.add(System.getenv("LOCALAPPDATA") + "/AndroidBuild/assets")

    androidResources {
        // o WebAssembly e os dados do OCR já são compactados; sem recompactar o app abre mais rápido
        noCompress += listOf("wasm", "traineddata")
    }
}

dependencies {
    implementation("androidx.webkit:webkit:1.17.1")
    implementation("androidx.core:core:1.17.0")
}
