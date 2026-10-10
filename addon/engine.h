// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "session.h"
#include <fcitx/inputmethodengine.h>
#include <fcitx/inputcontextproperty.h>
#include <fcitx/inputcontextmanager.h>
#include <fcitx/inputcontext.h>
namespace meltype {
struct State : fcitx::InputContextProperty {
    std::unique_ptr<Session> session;
    bool preedit=false;
    bool direct=false;
    bool alphanumericConversion=false;
};
struct MappedKey { int vk=0; int ch=0; int modifiers=0; };
MappedKey mapKey(const fcitx::Key &key);
// Unicode offsets in Fcitx are UCS4; core deletion lengths are UTF-16 units.
int deletionCharacters(const std::string &before, int utf16Units);
class Engine : public fcitx::InputMethodEngineV2 {
public:
    explicit Engine(fcitx::InputContextManager &manager);
    void keyEvent(const fcitx::InputMethodEntry &, fcitx::KeyEvent &) override;
    void reset(const fcitx::InputMethodEntry &, fcitx::InputContextEvent &) override;
    void deactivate(const fcitx::InputMethodEntry &, fcitx::InputContextEvent &) override;
    void select(fcitx::InputContext *ic, int index);
    std::string subMode(const fcitx::InputMethodEntry &, fcitx::InputContext &) override;
    std::string subModeLabelImpl(const fcitx::InputMethodEntry &, fcitx::InputContext &) override;
private:
    bool apply(fcitx::InputContext *ic, const nlohmann::json &value);
    void clear(fcitx::InputContext *ic) noexcept;
    void recover(fcitx::InputContext *ic, State *state) noexcept;
    fcitx::SimpleInputContextPropertyFactory<State> factory_;
};
}
