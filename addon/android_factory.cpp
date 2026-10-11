// SPDX-License-Identifier: GPL-3.0-or-later
#include "engine.h"
#include "meltype_mozc_bridge.h"
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/log.h>
#include <filesystem>
#include <cstdlib>
class AndroidMeltypeFactory : public fcitx::AddonFactory {
public:
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        try {
            // Supplied from the host internal appData path; never external storage.
            const char *dataPath=std::getenv("MELTYPE_DATA_DIR");
            if(!dataPath || !std::filesystem::path(dataPath).is_absolute()) throw std::runtime_error("Missing host private data directory");
            auto data=std::filesystem::path(dataPath);
            if(!meltype_set_data_directory(data.c_str())) throw std::runtime_error("Core data directory initialization failed");
            auto profile=data/"mozc";
            std::filesystem::create_directories(profile);
            if(!meltype_mozc_bridge_init(profile.c_str())) throw std::runtime_error("Mozc bridge initialization failed");
            if(!meltype_init(meltype_mozc_clauses,meltype_mozc_candidates,nullptr)) throw std::runtime_error("Callback initialization failed");
            meltype_set_prediction_callback(meltype_mozc_predictions);
            return new meltype::Engine(manager->instance()->inputContextManager());
        } catch(const std::exception &) {
            // Input text and private storage paths are never written to logs.
            FCITX_ERROR()<<"Meltype Android initialization failed";
            return nullptr;
        }
    }
};
FCITX_ADDON_FACTORY(AndroidMeltypeFactory)
