// SPDX-License-Identifier: GPL-3.0-or-later
#include "engine.h"
#include <fcitx/inputpanel.h>
#include <fcitx/candidatelist.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
int creates=0,destroys=0,mode=0;
extern "C" {
void *meltype_create() { ++creates;return mode==1?nullptr:reinterpret_cast<void *>(1); }
void meltype_destroy(void *) { ++destroys; }
void meltype_free(void *p) { std::free(p); }
char *meltype_handle_key(void *,int,int,int,const char *,const char *) {
    if(mode==4) return strdup("{\"consumed\":true,\"commits\":[],\"view\":{\"text\":\"\",\"converting\":false,\"selectedIndex\":-1,\"hint\":\"\",\"candidates\":[\"です\"]}}");
    if(mode==2) return strdup("invalid-json");
    if(mode==3) return strdup("{\"consumed\":true,\"commits\":[{\"deleteBefore\":9,\"text\":\"bad\"}],\"view\":null}");
    return strdup("{\"consumed\":true,\"commits\":[],\"view\":{\"text\":\"a\",\"converting\":false,\"selectedIndex\":0,\"hint\":\"\",\"candidates\":[]}}");
}
char *meltype_commit(void *) { return strdup("{\"consumed\":true,\"commits\":[],\"view\":null}"); }
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
 auto require=[](bool b){if(!b)throw std::runtime_error("failure recovery test failed");};
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
 std::cout<<"initialization, JSON and unsafe deletion recovery PASS\n";
 }catch(const std::exception &e){std::cerr<<e.what()<<"\n";return 1;}
}
