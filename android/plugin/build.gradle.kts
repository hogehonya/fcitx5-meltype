// SPDX-License-Identifier: GPL-3.0-or-later
plugins {
    id("org.fcitx.fcitx5.android.app-convention")
    id("org.fcitx.fcitx5.android.plugin-app-convention")
    id("org.fcitx.fcitx5.android.native-app-convention")
    id("org.fcitx.fcitx5.android.build-metadata")
    id("org.fcitx.fcitx5.android.data-descriptor")
    id("org.fcitx.fcitx5.android.fcitx-component")
}
// CMake validates inputs when this plugin is built. Other host tasks may be
// configured without downloading or building the Meltype provider.
fun requiredInput(name: String): String = providers.gradleProperty(name).orNull ?: ""
val nativeCore = requiredInput("meltypeCoreLibrary")
val mozcSource = requiredInput("meltypeMozcSourceDir")
val mozcData = requiredInput("meltypeMozcDataHeader")
val hostProtoc = requiredInput("meltypeHostProtoc")
val jsonHeaders = requiredInput("meltypeJsonIncludeDir")
val bridgeSource = providers.gradleProperty("meltypeBridgeSourceDir").orNull
val stageNativeCore = tasks.register<Sync>("stageNativeCore") {
    from(nativeCore)
    into(layout.buildDirectory.dir("generated/nativeCore/arm64-v8a"))
    onlyIf { nativeCore.isNotBlank() }
}
tasks.named("preBuild") { dependsOn(stageNativeCore) }
android {
    namespace = "org.fcitx.fcitx5.android.plugin.meltype"
    sourceSets.getByName("main").jniLibs.srcDir(layout.buildDirectory.dir("generated/nativeCore").get().asFile)
    defaultConfig {
        applicationId = "org.fcitx.fcitx5.android.plugin.meltype"
        minSdk = 24 // Android linker DT_RUNPATH/$ORIGIN support.
        externalNativeBuild {
            cmake {
                abiFilters += "arm64-v8a"
                targets("meltype")
                bridgeSource?.let { arguments("-DMELTYPE_BRIDGE_SOURCE_DIR=$it") }
                arguments(
                    "-DMELTYPE_NATIVE_LIBRARY=$nativeCore",
                    "-DMOZC_SOURCE_DIR=$mozcSource",
                    "-DMOZC_DATA_HEADER=$mozcData",
                    "-DPROTOC_EXECUTABLE=$hostProtoc",
                    "-DMELTYPE_JSON_INCLUDE_DIR=$jsonHeaders"
                )
            }
        }
    }
    splits.abi { reset(); include("arm64-v8a") }
    buildFeatures { resValues = true }
    buildTypes {
        release { resValue("string", "app_name", "@string/app_name_release") }
        debug { resValue("string", "app_name", "@string/app_name_debug") }
    }
    packaging.jniLibs {
        // These providers already belong to the host IME process.
        excludes += setOf("**/libc++_shared.so", "**/libFcitx5*")
    }
}
dependencies {
    implementation(project(":lib:fcitx5"))
    implementation(project(":lib:plugin-base"))
}
