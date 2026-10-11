// SPDX-License-Identifier: GPL-3.0-or-later
#include "engine.h"
#include <fcitx/inputpanel.h>
#include <fcitx/candidatelist.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
int creates=0,destroys=0,mode=0,commitCalls=0;
bool pending=false;
extern "C" {
void *meltype_create() { ++creates;return mode==1?nullptr:reinterpret_cast<void *>(1); }
void meltype_destroy(void *) { ++destroys; pending=false; }
void meltype_free(void *p) { std::free(p); }
char *meltype_handle_key(void *,int,int,int,const char *,const char *) {
    if(mode==5) { pending=true; return strdup("{\"consumed\":true,\"commits\":[],\"view\":{\"text\":\"日本語\",\"converting\":true,\"selectedIndex\":0,\"hint\":\"\",\"candidates\":[\"日本語\",\"にほんご\"]}}"); }
    if(mode==4) return strdup("{\"consumed\":true,\"commits\":[],\"view\":{\"text\":\"\",\"converting\":false,\"selectedIndex\":-1,\"hint\":\"\",\"candidates\":[\"です\"]}}");
    if(mode==2) return strdup("invalid-json");
    if(mode==3) return strdup("{\"consumed\":true,\"commits\":[{\"deleteBefore\":9,\"text\":\"bad\"}],\"view\":null}");
    return strdup("{\"consumed\":true,\"commits\":[],\"view\":{\"text\":\"a\",\"converting\":false,\"selectedIndex\":0,\"hint\":\"\",\"candidates\":[]}}");
}
char *meltype_commit(void *) { ++commitCalls;
 if(mode==5 && pending) { pending=false; return strdup("{\"consumed\":true,\"commits\":[{\"text\":\"日本語\",\"deleteBefore\":0}],\"view\":null}"); }
 return strdup("{\"consumed\":true,\"commits\":[],\"view\":null}"); }
char *meltype_select_candidate(void *,int) { return meltype_commit(nullptr); }
}
class Context:public fcitx::InputContext {
public:
 explicit Context(fcitx::InputContextManager &m):InputContext(m){created();}
 ~Context() override{destroy();}
 const char *frontend()const override{return "failure-test";}
 void commitStringImpl(const std::string &)override{++commits;}
 void deleteSurroundingTextImpl(int,unsigned int)override{++deletes;}
 void forwardKeyImpl(const fcitx::ForwardKeyEvent &)override{}
 void updatePreeditImpl()override{}
 int commits=0,deletes=0;
};
int main(){
 try {
 fcitx::InputContextManager manager;meltype::Engine engine(manager);Context context(manager);
 auto require=[](bool b,const char *message="failure recovery test failed"){if(!b)throw std::runtime_error(message);};
 auto send=[&]{fcitx::KeyEvent e(&context,fcitx::Key(FcitxKey_a));engine.keyEvent(fcitx::InputMethodEntry("meltype","Meltype","ja","meltype"),e);};
 require(creates==0); // Creating a Fcitx property must not initialize NativeAOT.
 mode=1;send();require(creates==1 && context.inputPanel().clientPreedit().empty());
 mode=0;send();require(creates==2 && !context.inputPanel().clientPreedit().empty());
 mode=2;send();require(destroys==1 && context.inputPanel().clientPreedit().empty());
 mode=0;send();require(creates==3); // Failed pending state is discarded.
 mode=3;send();require(destroys==2 && context.commits==0 && context.deletes==0);
 mode=0;send();require(creates==4);
 mode=4;send();require(context.inputPanel().clientPreedit().empty() && context.inputPanel().candidateList());
 fcitx::KeyEvent direct(&context,fcitx::Key(FcitxKey_Muhenkan));
 engine.keyEvent(fcitx::InputMethodEntry("meltype","Meltype","ja","meltype"),direct);
 require(direct.accepted() && !context.inputPanel().candidateList() && context.commits==0);
 const fcitx::InputMethodEntry entry("meltype","Meltype","ja","meltype");
 for(bool clientCommit : {true,false}) {
   Context sent(manager);
   if(clientCommit) sent.setCapabilityFlags(fcitx::CapabilityFlag::ClientUnfocusCommit);
   mode=5;
   fcitx::KeyEvent key(&sent,fcitx::Key(FcitxKey_a)); engine.keyEvent(entry,key);
   require(!sent.inputPanel().clientPreedit().empty());
   // Client sends current preedit, or framework ReservedFirst commits it.
   // The engine must never commit the same pending text again in either case.
   sent.commitString(sent.inputPanel().clientPreedit().toString());
   const auto calls=commitCalls;
   const auto created=creates, destroyed=destroys;
   fcitx::InputContextEvent focusOut(&sent,fcitx::EventType::InputContextFocusOut);
   engine.deactivate(entry,focusOut);
   require(sent.commits==1 && commitCalls==calls,"FocusOut must not recommit already submitted preedit");
   require(sent.inputPanel().clientPreedit().empty() && !sent.inputPanel().candidateList());
   require(destroys==destroyed+1);
   fcitx::KeyEvent next(&sent,fcitx::Key(FcitxKey_a)); engine.keyEvent(entry,next);
   require(creates==created+1 && !sent.inputPanel().clientPreedit().empty());
   fcitx::InputContextEvent reset(&sent,fcitx::EventType::InputContextReset);
   engine.reset(entry,reset);
   require(sent.commits==2 && sent.inputPanel().clientPreedit().empty());
   fcitx::KeyEvent switching(&sent,fcitx::Key(FcitxKey_a)); engine.keyEvent(entry,switching);
   fcitx::InputContextEvent change(&sent,fcitx::EventType::InputContextSwitchInputMethod);
   engine.deactivate(entry,change);
   require(sent.commits==3 && sent.inputPanel().clientPreedit().empty());
 }
 mode=4;
 Context nextWord(manager);
 fcitx::KeyEvent show(&nextWord,fcitx::Key(FcitxKey_a)); engine.keyEvent(entry,show);
 require(nextWord.inputPanel().clientPreedit().empty() && nextWord.inputPanel().candidateList());
 fcitx::InputContextEvent leave(&nextWord,fcitx::EventType::InputContextFocusOut);
 const auto calls=commitCalls;
 engine.deactivate(entry,leave);
 require(nextWord.commits==0 && commitCalls==calls && !nextWord.inputPanel().candidateList());
 std::cout<<"initialization, JSON and unsafe deletion recovery PASS\n";
 }catch(const std::exception &e){std::cerr<<e.what()<<"\n";return 1;}
}
