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
    std::cout<<"real NativeAOT/Fcitx context integration PASS\n";
 } catch(const std::exception &e) { std::cerr<<e.what()<<"\n";return 1; }
}
