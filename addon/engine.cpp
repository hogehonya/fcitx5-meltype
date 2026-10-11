// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Yukishiro
// Adapted from upstream Meltype; see ../NOTICE.
#include "engine.h"
#include <fcitx/candidatelist.h>
#include <fcitx/inputpanel.h>
#include <fcitx-utils/utf8.h>
#include <fcitx-utils/log.h>
#include <vector>
namespace meltype {
MappedKey mapKey(const fcitx::Key &key) {
    MappedKey out;
    auto flags=key.states();
    if (flags.test(fcitx::KeyState::Shift)) out.modifiers|=1;
    if (flags.test(fcitx::KeyState::Ctrl)) out.modifiers|=2;
    if (flags.test(fcitx::KeyState::Alt)) out.modifiers|=4;
    if (flags.test(fcitx::KeyState::Super) || flags.test(fcitx::KeyState::Super2)) out.modifiers|=8;
    switch (key.sym()) {
    case FcitxKey_Return: case FcitxKey_KP_Enter: out.vk=0x0d; return out;
    case FcitxKey_Tab: out.vk=9; return out;
    case FcitxKey_space: out.vk=0x20; out.ch=0x20; return out;
    case FcitxKey_BackSpace: out.vk=8; return out;
    case FcitxKey_Delete: out.vk=0x2e; return out;
    case FcitxKey_Escape: out.vk=0x1b; return out;
    case FcitxKey_Left: out.vk=0x25; return out;
    case FcitxKey_Up: out.vk=0x26; return out;
    case FcitxKey_Right: out.vk=0x27; return out;
    case FcitxKey_Down: out.vk=0x28; return out;
    case FcitxKey_Home: out.vk=0x24; return out;
    case FcitxKey_End: out.vk=0x23; return out;
    case FcitxKey_Page_Up: out.vk=0x21; return out;
    case FcitxKey_Page_Down: out.vk=0x22; return out;
    case FcitxKey_F6: case FcitxKey_F7: case FcitxKey_F8: case FcitxKey_F9: case FcitxKey_F10:
        out.vk=0x75+(key.sym()-FcitxKey_F6); return out;
    default: break;
    }
    auto ch=fcitx::Key::keySymToUnicode(key.sym());
    // Native ABI accepts one UTF-16 code unit; pass non-BMP keys through intact.
    if (ch<0x20 || ch>0xffff || (ch>=0xd800 && ch<=0xdfff)) return out;
    out.ch=ch;
    if (ch>='a' && ch<='z') out.vk=ch-'a'+'A';
    else if ((ch>='A' && ch<='Z') || (ch>='0' && ch<='9')) out.vk=ch;
    else {
        switch(ch) {
        case ',': out.vk=0xbc; break; case '.': out.vk=0xbe; break;
        case '-': out.vk=0xbd; break; case '/': out.vk=0xbf; break;
        case '[': out.vk=0xdb; break; case ']': out.vk=0xdd; break;
        default: out.vk=7;
        }
    }
    return out;
}
static std::vector<std::pair<size_t,uint32_t>> characters(const std::string &s) {
    std::vector<std::pair<size_t,uint32_t>> chars;
    auto it=s.begin();
    while(it!=s.end()) {
        uint32_t ch;
        auto next=fcitx::utf8::getNextChar(it,s.end(),&ch);
        if(next==it || !fcitx::utf8::UCS4IsValid(ch)) throw std::runtime_error("Invalid UTF-8");
        chars.emplace_back(static_cast<size_t>(it-s.begin()),ch); it=next;
    }
    return chars;
}
int deletionCharacters(const std::string &before,int units) {
    auto chars=characters(before);
    int count=0;
    for(auto it=chars.rbegin();units>0 && it!=chars.rend();++it) {
        units-=it->second>0xffff?2:1; ++count;
    }
    if(units!=0) throw std::runtime_error("Deletion exceeds surrounding text or splits a surrogate pair");
    return count;
}
static std::pair<std::string,std::string> surrounding(fcitx::InputContext *ic) {
    if(ic->capabilityFlags().testAny(fcitx::CapabilityFlag::PasswordOrSensitive)) return {};
    const auto &s=ic->surroundingText();
    if(!s.isValid() || s.cursor()!=s.anchor()) return {};
    auto chars=characters(s.text());
    if(s.cursor()>chars.size()) return {};
    size_t byte=s.cursor()==chars.size()?s.text().size():chars[s.cursor()].first;
    return {s.text().substr(0,byte),s.text().substr(byte)};
}
class Candidate : public fcitx::CandidateWord {
public:
    Candidate(Engine *engine,int index,const std::string &text)
        : CandidateWord(fcitx::Text(text)),engine_(engine),index_(index) {}
    void select(fcitx::InputContext *ic) const override { engine_->select(ic,index_); }
private:
    Engine *engine_; int index_;
};
Engine::Engine(fcitx::InputContextManager &manager) {
    if(!manager.registerProperty("meltypeSession",&factory_)) throw std::runtime_error("Cannot register Meltype session");
}
void Engine::clear(fcitx::InputContext *ic) noexcept {
    try {
        ic->inputPanel().reset();
        ic->updatePreedit();
        ic->updateUserInterface(fcitx::UserInterfaceComponent::InputPanel);
    } catch(...) { /* Host callbacks cannot escape an error recovery path. */ }
}
void Engine::recover(fcitx::InputContext *ic,State *state) noexcept {
    if(state) { state->session.reset(); state->preedit=false; state->alphanumericConversion=false; }
    clear(ic);
}
bool Engine::apply(fcitx::InputContext *ic,const nlohmann::json &value) {
    const auto &commits=value.at("commits");
    // Compute all deletion offsets before any client edit. Refuse unsafe deletion.
    auto [before,after]=surrounding(ic);
    std::vector<int> deletes;
    for(const auto &edit:commits) {
        auto n=deletionCharacters(before,edit.at("deleteBefore").get<int>());
        deletes.push_back(n);
        auto chars=characters(before);
        size_t keep=chars.size()-n;
        before=before.substr(0,keep==chars.size()?before.size():chars[keep].first)+edit.at("text").get<std::string>();
    }
    auto &panel=ic->inputPanel(); panel.reset();
    for(size_t i=0;i<commits.size();++i) {
        if(deletes[i]) ic->deleteSurroundingText(-deletes[i],deletes[i]);
        auto text=commits[i].at("text").get<std::string>();
        if(!text.empty()) ic->commitString(text);
    }
    auto *state=ic->propertyFor(&factory_); state->preedit=false;
    const auto &view=value.at("view");
    if(!view.is_null()) {
        auto text=view.at("text").get<std::string>();
        fcitx::Text preedit(text,fcitx::TextFormatFlag::Underline);
        preedit.setCursor(text.size()); panel.setClientPreedit(preedit);
        state->preedit=!text.empty();
#ifndef __ANDROID__
        panel.setAuxUp(fcitx::Text(view.at("hint").get<std::string>()));
#endif
        auto candidates=view.at("candidates").get<std::vector<std::string>>();
        const bool converting=view.at("converting").get<bool>();
        if((converting && candidates.size()>1) || (!converting && !candidates.empty())) {
            auto list=std::make_unique<fcitx::CommonCandidateList>();
            list->setPageSize(9); list->setLayoutHint(fcitx::CandidateLayoutHint::Vertical);
            list->setLabels();
            for(size_t i=0;i<candidates.size();++i) list->append<Candidate>(this,i,candidates[i]);
            auto index=view.at("selectedIndex").get<int>();
            if(index>=0 && static_cast<size_t>(index)<candidates.size()) list->setGlobalCursorIndex(index);
            panel.setCandidateList(std::move(list));
        }
    }
    ic->updatePreedit(); ic->updateUserInterface(fcitx::UserInterfaceComponent::InputPanel);
    if(state->alphanumericConversion && !state->preedit) {
        state->alphanumericConversion=false;
        // A cancelled conversion must not affect the next normal commit.
        if(!commits.empty()) {
            // F10 is a one-composition conversion, not an English context switch.
            state->session.reset();
        }
    }
    return value.at("consumed").get<bool>();
}
void Engine::keyEvent(const fcitx::InputMethodEntry &,fcitx::KeyEvent &event) {
    auto *ic=event.inputContext();
    if(event.isRelease() || ic->capabilityFlags().testAny(fcitx::CapabilityFlag::PasswordOrSensitive)) return;
    if(event.key().isModifier()) return;
    State *state=nullptr;
    try {
        state=ic->propertyFor(&factory_);
        const auto sym=event.key().sym();
        const bool modeKey=sym==FcitxKey_Muhenkan || sym==FcitxKey_Henkan ||
            sym==FcitxKey_Hiragana || sym==FcitxKey_Hiragana_Katakana;
        if(modeKey) {
            // Modified mode keys belong to application/global shortcuts.
            if(event.key().states()) return;
            if(state->session) apply(ic,state->session->commit());
            state->direct=sym==FcitxKey_Muhenkan;
            ic->updateUserInterface(fcitx::UserInterfaceComponent::StatusArea);
            event.filterAndAccept();
            return;
        }
        if(state->direct) return;
        auto key=mapKey(event.key());
        if(!key.vk) {
            // Preserve text order when a non-BMP/unhandled key passes to the app.
            if(state->session) apply(ic,state->session->commit());
            return;
        }
        if(!key.modifiers && state->preedit) {
            if(sym==FcitxKey_F10) state->alphanumericConversion=true;
            else if(sym==FcitxKey_F6 || sym==FcitxKey_F7 || sym==FcitxKey_F9)
                state->alphanumericConversion=false;
        }
        if(!state->session) state->session=std::make_unique<Session>();
        auto [before,after]=state->preedit?std::pair<std::string,std::string>{}:surrounding(ic);
        auto value=state->session->key(key.vk,key.ch,key.modifiers,
            state->preedit?nullptr:before.c_str(),state->preedit?nullptr:after.c_str());
        if(apply(ic,value)) event.filterAndAccept();
    } catch(const std::exception &) {
        FCITX_ERROR() << "Meltype key processing failed";
        recover(ic,state);
    }
}
std::string Engine::subMode(const fcitx::InputMethodEntry &,fcitx::InputContext &ic) {
    return ic.propertyFor(&factory_)->direct?"英字直接入力":"Meltype 自動判定";
}
std::string Engine::subModeLabelImpl(const fcitx::InputMethodEntry &,fcitx::InputContext &ic) {
    return ic.propertyFor(&factory_)->direct?"A":"あ";
}
void Engine::reset(const fcitx::InputMethodEntry &,fcitx::InputContextEvent &event) {
    auto *ic=event.inputContext(); State *state=nullptr;
    try {
        state=ic->propertyFor(&factory_);
        if(state->session) apply(ic,state->session->commit());
        else clear(ic);
    } catch(const std::exception &) { FCITX_ERROR() << "Meltype reset failed"; recover(ic,state); }
}
void Engine::deactivate(const fcitx::InputMethodEntry &entry,fcitx::InputContextEvent &event) {
    if(event.type()!=fcitx::EventType::InputContextFocusOut) { reset(entry,event); return; }
    // Fcitx already commits client preedit, unless ClientUnfocusCommit delegates
    // it to the client. Never submit that same text again on focus loss.
    auto *ic=event.inputContext();
    try { recover(ic,ic->propertyFor(&factory_)); }
    catch(const std::exception &) { clear(ic); }
}
void Engine::select(fcitx::InputContext *ic,int index) {
    State *state=nullptr;
    try {
        state=ic->propertyFor(&factory_);
        if(state->session) apply(ic,state->session->select(index));
    } catch(const std::exception &) { FCITX_ERROR() << "Meltype candidate selection failed"; recover(ic,state); }
}
}
