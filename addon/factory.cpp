// SPDX-License-Identifier: GPL-3.0-or-later
#include "engine.h"
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/log.h>
#include <filesystem>
#include <cstdlib>
class MeltypeFactory : public fcitx::AddonFactory {
public:
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override {
        try {
            const char *helper=std::getenv("MELTYPE_MOZC_HELPER");
            if(!helper || !std::filesystem::path(helper).is_absolute()) throw std::runtime_error("Absolute helper path required");
            const char *profile=std::getenv("MELTYPE_MOZC_PROFILE");
            if(profile && !std::filesystem::path(profile).is_absolute()) throw std::runtime_error("Absolute profile path required");
            if(!meltype_init_mozc(helper,profile)) throw std::runtime_error("Mozc initialization failed");
            return new meltype::Engine(manager->instance()->inputContextManager());
        } catch(const std::exception &) {
            FCITX_ERROR() << "Meltype initialization failed: check MELTYPE_MOZC_HELPER and profile";
            return nullptr;
        }
    }
};
FCITX_ADDON_FACTORY(MeltypeFactory)
