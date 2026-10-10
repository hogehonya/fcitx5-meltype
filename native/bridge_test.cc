// SPDX-License-Identifier: GPL-3.0-or-later
#include "mozc_bridge.h"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
int main(int argc, char** argv) {
 try {
  check(argc==2,"profile argument");
  check(!meltype_mozc_clauses("はし",nullptr),"uninitialized");
  check(!meltype_mozc_bridge_init("relative"),"relative path rejected");
  for (int cycle=0; cycle<2; ++cycle) {
   check(meltype_mozc_bridge_init(argv[1]),"init");
   check(meltype_mozc_bridge_init(argv[1]),"idempotent init");
   check(!meltype_mozc_bridge_init("/different-profile"),"different profile rejected");
   check(!meltype_mozc_clauses("",nullptr),"empty clauses");
   check(!meltype_mozc_candidates(nullptr),"null reading");
   for (int i=0;i<10;++i) {
    char* clauses=meltype_mozc_clauses("きょうは",nullptr);
    check(clauses && std::strchr(clauses,'\t'),"Japanese clauses"); std::free(clauses);
    char* candidates=meltype_mozc_candidates("はし");
    check(candidates && std::strstr(candidates,"橋") && std::strchr(candidates,'\n'),"multiple candidates"); std::free(candidates);
   }
   meltype_mozc_bridge_shutdown(); meltype_mozc_bridge_shutdown();
   check(!meltype_mozc_candidates("はし"),"shutdown");
  }
  std::cout<<"bridge tests passed\n";
  return 0;
 } catch (const std::exception& e) { std::cerr<<e.what()<<"\n"; return 1; }
}
