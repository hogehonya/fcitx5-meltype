// SPDX-License-Identifier: GPL-3.0-or-later
#include "engine.h"
#include <fcitx/inputpanel.h>
#include <fcitx/candidatelist.h>
#include <iostream>
#include <filesystem>
#include <cstdlib>
#include <stdexcept>
void require(bool condition,const char *message) { if(!condition) throw std::runtime_error(message); }
class Context : public fcitx::InputContext {
public:
    explicit Context(fcitx::InputContextManager &manager) : InputContext(manager) { created(); }
    ~Context() override { destroy(); }
    const char *frontend() const override { return "meltype-test"; }
    std::string committed;
    void commitStringImpl(const std::string &s) override { committed+=s; }
    void deleteSurroundingTextImpl(int,unsigned int) override {}
    void forwardKeyImpl(const fcitx::ForwardKeyEvent &) override {}
    void updatePreeditImpl() override {}
};
int main() {
 try {
    const char *helper=std::getenv("MELTYPE_MOZC_HELPER");
    const char *profile=std::getenv("MELTYPE_MOZC_PROFILE");
    require(helper && profile,"Set isolated MELTYPE_MOZC_HELPER and MELTYPE_MOZC_PROFILE for real-core testing");
    require(meltype_init_mozc(helper,profile)==1,"Mozc initialization failed");
    require(meltype::mapKey(fcitx::Key(FcitxKey_a)).vk=='A',"letter map");
    require(meltype::mapKey(fcitx::Key(static_cast<fcitx::KeySym>(0x0101f600))).vk==0,"non-BMP must pass through");
    require(meltype::deletionCharacters("a😀日本",4)==3,"UTF16 to UCS4 deletion");
    bool rejected=false; try { meltype::deletionCharacters("😀",1); } catch(...) { rejected=true; }
    require(rejected,"surrogate split must fail");
    bool missing=false; try { meltype::result(nullptr); } catch(...) { missing=true; }
    require(missing,"NULL ABI result rejected");
    fcitx::InputContextManager manager;
    meltype::Engine engine(manager);
    Context a(manager),b(manager);
    auto send=[&](Context &ic,fcitx::KeySym sym,bool release=false) {
        fcitx::KeyEvent event(&ic,fcitx::Key(sym),release);
        engine.keyEvent(fcitx::InputMethodEntry{"meltype","Meltype","ja","meltype"},event);
        return event.accepted();
    };
    auto type=[&](Context &ic,const std::string &s) { for(unsigned char c:s) send(ic,static_cast<fcitx::KeySym>(c)); };
    type(a,"kyouhagithubnipushshita");
    require(a.inputPanel().clientPreedit().toString()=="今日はgithubにpushした","mixed preedit");
    type(b,"hello"); send(b,FcitxKey_Return);
    require(b.committed=="hello","English commit/session independence");
    require(a.committed.empty(),"other context must not commit");
    send(a,FcitxKey_Return);
    require(a.committed=="今日はgithubにpushした","mixed commit");
    type(a,"hashi"); send(a,FcitxKey_space); send(a,FcitxKey_space);
    auto list=a.inputPanel().candidateList();
    require(list && list->size()>1,"multiple candidates");
    auto selected=list->candidate(1).text().toString();
    list->candidate(1).select(&a);
    send(a,FcitxKey_Return);
    require(a.committed.find(selected)!=std::string::npos,"candidate click commit");
    send(b,FcitxKey_a,true); require(b.inputPanel().clientPreedit().empty(),"release ignored");
    b.setCapabilityFlags(fcitx::CapabilityFlag::Password);
    send(b,FcitxKey_a); require(b.inputPanel().clientPreedit().empty(),"password pass-through");
    b.setCapabilityFlags(fcitx::CapabilityFlags()); type(b,"nihon");
    fcitx::InputContextEvent reset(&b,fcitx::EventType::InputContextReset);
    engine.reset(fcitx::InputMethodEntry{"meltype","Meltype","ja","meltype"},reset);
    require(!b.committed.empty() && b.inputPanel().clientPreedit().empty(),"reset commits and clears");
    auto prefix=b.committed;
    type(b,"nihona");
    auto pending=b.inputPanel().clientPreedit().toString();
    require(!pending.empty(),"pending before emoji");
    send(b,FcitxKey_Shift_L);
    require(b.committed==prefix && b.inputPanel().clientPreedit().toString()==pending,"modifier preserves pending");
    send(b,FcitxKey_a);
    require(b.committed==prefix && b.inputPanel().clientPreedit().toString()!=pending,"input continues after modifier");
    pending=b.inputPanel().clientPreedit().toString();
    require(!send(b,static_cast<fcitx::KeySym>(0x0101f600)),"emoji key pass-through");
    require(b.committed==prefix+pending && b.inputPanel().clientPreedit().empty(),"pending commit precedes non-BMP key");
    Context direct(manager),normal(manager);
    const fcitx::InputMethodEntry entry{"meltype","Meltype","ja","meltype"};
    type(direct,"nihongo");
    auto expected=direct.inputPanel().clientPreedit().toString();
    require(send(direct,FcitxKey_Muhenkan),"Muhenkan consumed");
    require(direct.committed==expected && direct.inputPanel().clientPreedit().empty(),"mode change commits pending once");
    require(engine.subModeLabel(entry,direct)=="A","direct mode visible");
    for(auto key: {FcitxKey_a,FcitxKey_A,FcitxKey_space,FcitxKey_exclam,FcitxKey_BackSpace})
        require(!send(direct,key),"direct keys pass to application");
    require(!send(direct,FcitxKey_Henkan,true),"mode key release ignored");
    fcitx::KeyEvent shortcut(&direct,fcitx::Key(FcitxKey_Henkan,fcitx::KeyState::Ctrl));
    engine.keyEvent(entry,shortcut);
    require(!shortcut.accepted() && engine.subModeLabel(entry,direct)=="A","modified mode key preserved");
    type(normal,"nihongo");
    require(normal.inputPanel().clientPreedit().toString()=="日本語","mode is context local");
    fcitx::InputContextEvent leave(&direct,fcitx::EventType::InputContextReset);
    engine.deactivate(entry,leave);
    require(engine.subModeLabel(entry,direct)=="A" && direct.committed==expected,"deactivation retains mode without double commit");
    require(send(direct,FcitxKey_Henkan),"Henkan returns to automatic mode");
    type(direct,"nihongo");
    require(direct.inputPanel().clientPreedit().toString()=="日本語","normal Meltype resumes");
    send(direct,FcitxKey_space);
    auto candidate=direct.inputPanel().clientPreedit().toString();
    send(direct,FcitxKey_Muhenkan); send(direct,FcitxKey_Muhenkan);
    require(direct.committed==expected+candidate,"candidate mode change commits exactly once");
    require(send(direct,FcitxKey_Hiragana) && engine.subModeLabel(entry,direct)=="あ","Hiragana resumes automatic mode");
    fcitx::KeyEvent locks(&direct,fcitx::Key(FcitxKey_Muhenkan,fcitx::KeyStates(fcitx::KeyState::CapsLock)|fcitx::KeyState::NumLock));
    engine.keyEvent(entry,locks);
    require(locks.accepted() && engine.subModeLabel(entry,direct)=="A","lock states do not suppress mode key");
    for(auto mode : {FcitxKey_F6,FcitxKey_F7}) {
        for(bool candidates : {false,true}) {
            Context kana(manager);
            type(kana,"nihongo");
            if(candidates) send(kana,FcitxKey_space);
            require(send(kana,mode),"kana conversion consumed");
            auto reading=mode==FcitxKey_F6 ? "にほんご" : "ニホンゴ";
            require(kana.inputPanel().clientPreedit().toString()==reading,"whole composition kana conversion");
            require(!kana.inputPanel().candidateList() || kana.inputPanel().candidateList()->empty(),"kana conversion clears candidates");
            send(kana,FcitxKey_Return);
            require(kana.committed==reading,"kana commit exact");
            type(kana,"nihongo");
            require(kana.inputPanel().clientPreedit().toString()=="日本語","kana conversion is not persistent");
        }
    }
    Context alphanumeric(manager);
    for(int n=0;n<2;++n) {
        type(alphanumeric,"nihongo");
        require(send(alphanumeric,FcitxKey_F10),"F10 consumed");
        require(alphanumeric.inputPanel().clientPreedit().toString()=="nihongo","half width preedit");
        send(alphanumeric,FcitxKey_Return);
    }
    require(alphanumeric.committed=="nihongonihongo","half width exact commits");
    type(alphanumeric,"nihongo");
    require(alphanumeric.inputPanel().clientPreedit().toString()=="日本語","F10 does not carry English context to next composition");
    Context englishContext(manager);
    for(int n=0;n<2;++n) { type(englishContext,"hello"); send(englishContext,FcitxKey_Return); }
    type(englishContext,"nihongo");
    const auto englishContinuation=englishContext.inputPanel().clientPreedit().toString();
    for(bool erase : {false,true}) {
        Context cancelled(manager);
        type(cancelled,"nihongo"); send(cancelled,FcitxKey_F10);
        if(erase) for(int n=0;n<7;++n) send(cancelled,FcitxKey_BackSpace);
        else send(cancelled,FcitxKey_Escape);
        require(cancelled.inputPanel().clientPreedit().empty(),"cancel F10 clears composition");
        require(cancelled.committed.empty(),"cancel F10 does not commit text");
        for(int n=0;n<2;++n) { type(cancelled,"hello"); send(cancelled,FcitxKey_Return); }
        require(cancelled.committed=="hellohello","normal commits after F10 cancel");
        type(cancelled,"nihongo");
        require(cancelled.inputPanel().clientPreedit().toString()==englishContinuation,"F10 cancellation preserves subsequent normal English context");
    }
    std::cout<<"real NativeAOT/Fcitx context integration PASS\n";
 } catch(const std::exception &e) { std::cerr<<e.what()<<"\n";return 1; }
}
