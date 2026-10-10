// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "meltype_abi.h"
#include <memory>
#include <stdexcept>
#include <nlohmann/json.hpp>
#ifdef __ANDROID__
static_assert(NLOHMANN_JSON_VERSION_MAJOR == 3 && NLOHMANN_JSON_VERSION_MINOR == 11 && NLOHMANN_JSON_VERSION_PATCH == 3, "Android build pins nlohmann-json 3.11.3");
#endif
namespace meltype {
inline nlohmann::json result(char *raw) {
    std::unique_ptr<char, decltype(&meltype_free)> owned(raw, meltype_free);
    if (!raw) throw std::runtime_error("Meltype returned no result");
    auto value = nlohmann::json::parse(raw);
    // Validate the entire result before modifying a client's text.
    value.at("consumed").get<bool>();
    for (const auto &edit : value.at("commits")) {
        if (edit.at("deleteBefore").get<int>() < 0) throw std::runtime_error("Negative deletion");
        edit.at("text").get<std::string>();
    }
    const auto &view = value.at("view");
    if (!view.is_null()) {
        view.at("text").get<std::string>();
        view.at("converting").get<bool>();
        view.at("selectedIndex").get<int>();
        view.at("hint").get<std::string>();
        view.at("candidates").get<std::vector<std::string>>();
    }
    return value;
}
class Session {
public:
    Session() : handle_(meltype_create()) {
        if (!handle_) throw std::runtime_error("Meltype session initialization failed");
    }
    ~Session() { meltype_destroy(handle_); }
    Session(const Session &) = delete;
    Session &operator=(const Session &) = delete;
    nlohmann::json key(int vk, int ch, int mods, const char *before=nullptr, const char *after=nullptr) {
        return result(meltype_handle_key(handle_,vk,ch,mods,before,after));
    }
    nlohmann::json commit() { return result(meltype_commit(handle_)); }
    nlohmann::json select(int index) { return result(meltype_select_candidate(handle_,index)); }
private:
    void *handle_;
};
}
