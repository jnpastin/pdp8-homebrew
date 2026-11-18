# Test Programs

## 1. Purpose

DEC MAINDEC-8E diagnostic programs used to validate the simulator, with their provenance. Each program is loaded into the simulator through console DEPOSIT, so the console microcode runs too.

The files are data: paper-tape images in DEC BIN format (`-pb`), octal dumps of those tapes (`.od`), label text or photographs (`.lbl`, `.lbl.jpg`), and program write-ups (`-d.pdf`). Nothing here is executed on the host.

## 2. Source

All files come from the MAINDEC-8E collection of the deramp.com DEC archive:

```text
https://deramp.com/downloads/mfe_archive/011-Digital%20Equipment%20Corporation/01%20DEC%20PDP-8%20Family%20Software/03%20MAINDEC%20Maintenance%20progams/MAINDEC%208E/
```

Each program came from the sub-folder named in section 3, retrieved on 2026-11-18. Where a folder holds several revisions, the latest tape revision was taken.

## 3. Programs

| Directory | Program | Folder | Phase | Notes |
|---|---|---|---|---|
| `maindec-8e-d0ab` | D0AB Instruction Test 1 | `MAINDEC-8E D0A PDP8E Instruction Test 1` | 1 | |
| `maindec-8e-d0bb` | D0BB Instruction Test 2 | `MAINDEC-8E D0B PDP8E Instruction Test 2` | 1 | |
| `maindec-8e-d0cc` | D0CC Adder Test | `MAINDEC-8E D0C PDP8E Adder Test` | 1 | |
| `maindec-8e-d0db` | D0DB Random AND Test | `MAINDEC-8E D0D PDP8E Random AND Test` | 1 | |
| `maindec-8e-d0eb` | D0EB Random TAD Test | `MAINDEC-8E D0E Random TAD Test` | 1 | |
| `maindec-8e-d0fc` | D0FC Random ISZ Test | `MAINDEC-8E D0F Random ISZ Test` | 1 | |
| `maindec-8e-d0gc` | D0GC Random DCA Test | `MAINDEC-8E D0G Random DCA Test` | 1 | no label file in the archive |
| `maindec-8e-d0hc` | D0HC Random JMP Test | `MAINDEC-8E D0H Random JMP Test` | 1 | no label file in the archive |
| `maindec-8e-d0ib` | D0IB Basic JMP-JMS Test | `MAINDEC-8E D0I Basic JMP-JMS Test` | 1 | no label file in the archive |
| `maindec-8e-d0jc` | D0JC Random JMP-JMS Test | `MAINDEC-8E D0J Random JMP-JMS Test` | 1 | |
| `maindec-8e-d1aa` | D1AA MM8-E 4K Memory Checkerboard | `MAINDEC-8E D1A MM8E 4K Memory Checkerboard` | 2 | no write-up in the archive |
| `maindec-8e-d1bc` | D1BC KM8-E Extended Memory Checkerboard | `MAINDEC-8E D1B KM8E Extended Memory Checkerboard` | 2 | no write-up; the archive's note says it prints "5" on the teletype after each pass, so it needs the console controller |
| `maindec-8e-d1ec` | D1EC Memory Address Test | `MAINDEC-8E D1E Memory Address Test` | 2 | |
| `maindec-8e-d1fb` | D1FB Extended Memory Address Test | `MAINDEC-8E D1F Extended Memory Address Test` | 2 | |
| `maindec-8e-d1ha` | D1HA Memory Extension and Time Share Control Test | `MAINDEC-8E D1H Memory Extension and Timeshare Control Test` | 2 | the D1HB write-up is included, but the archive holds only the D1HA tape; time-share (user mode) is not implemented |
| `maindec-8e-d2ab` | D2AB Teletype KL8 Data Control Test | `MAINDEC-8E D2A PDP8E Teletype-KL8 Data Control Test` | 3 | |
| `maindec-8e-d2ca` | D2CA High Speed Reader Punch Tests | `MAINDEC-8E D2CA High Speed Reader Punch Tests` | 3 | no write-up in the archive |

## 4. Integrity

SHA-256 of every file, as retrieved.

| File | Bytes | SHA-256 |
|---|---|---|
| `maindec-8e-d0ab/maindec-8E-d0ab-d.pdf` | 2243793 | `3f8e87e933115238517c98264bd74245283b14417bd9883d462c60431cc155b8` |
| `maindec-8e-d0ab/maindec-8E-d0ab-pb` | 5621 | `062e75832f6d355e1fdf1d66f1eb39738eb5869db28f901d806314015b2934b5` |
| `maindec-8e-d0ab/maindec-8E-d0ab-pb.od` | 28105 | `a46a95be267ed3bc4cdfcd763b67b93769b208c84b8c81eca1cb4664a6837a99` |
| `maindec-8e-d0bb/maindec-8E-d0bb-d.pdf` | 1587201 | `ac506c4d8ec35239d9de1672e5548d9acb4baa775e050f6f973087bd9187ca4b` |
| `maindec-8e-d0bb/maindec-8E-d0bb-pb` | 4216 | `d98b15f8184ceb1139bae3cbd8cf27fd61ca7414f4c815de3f232a9d1c089b5d` |
| `maindec-8e-d0bb/maindec-8E-d0bb-pb.od` | 21080 | `e631e3eb57aba17316e42c9a03b8fcd165fc997b29539f5ba83bc2e884858ce1` |
| `maindec-8e-d0cc/maindec-8E-d0cc-d.pdf` | 4825435 | `71e024f30251698fa5f9351bf8ab63de1122cf105fa35e413ba22d0f931b8d40` |
| `maindec-8e-d0cc/maindec-8E-d0cc-pb` | 4905 | `6a1343f55412cb006c89056107a9452c25af0c2788fefd250e690714265fb692` |
| `maindec-8e-d0cc/maindec-8E-d0cc-pb.lbl` | 44 | `7ecaa16dddc98d20021c4fbe1e4cabc3be31aa2e7dff90cdb7a8b50c6bfc2007` |
| `maindec-8e-d0cc/maindec-8E-d0cc-pb.od` | 24525 | `38ff54369740b2fba9126914c69f47d620026484007467bf7d16f32c4bea3bd5` |
| `maindec-8e-d0db/maindec-8E-d0db-d.pdf` | 519258 | `1c916c82e926345382b8cb28901a498dd69015a6badc323849adddc3584c57d4` |
| `maindec-8e-d0db/maindec-8E-d0db-pb` | 1006 | `ee529c9e91993cc70eb147e7cd0cbaa06ed70207a153a2480d8dfcdbad99dcec` |
| `maindec-8e-d0db/maindec-8E-d0db-pb.lbl` | 45 | `586a7150ed23dfa8ce0b1ea6c6a609285cbf679d78b3e391209123b5d934cab6` |
| `maindec-8e-d0db/maindec-8E-d0db-pb.od` | 5030 | `73187c5220d7ea2f7ac7abc6a206d0bd4842011a8502f5d2d15d90367d1fe86c` |
| `maindec-8e-d0eb/maindec-8E-d0eb-d.pdf` | 473287 | `b4a8a4b7b0aea5dfba2c23eb30324dd618cd007cf1d584db4cdc04d1a225ba67` |
| `maindec-8e-d0eb/maindec-8E-d0eb-pb` | 1062 | `2b43a0302053a649b89dac1a58613b13dc3b370d9f7190ac087a0da118c1ee98` |
| `maindec-8e-d0eb/maindec-8E-d0eb-pb.lbl` | 45 | `85ef5ead6b8f85d891b1f16e0bd387ab9503714f791fbd29f106ad1a0cea9acc` |
| `maindec-8e-d0eb/maindec-8E-d0eb-pb.od` | 6372 | `ff220e27738a95e51418ca4a289fc3099fb8a7a2779d6e77209bd04ab20a8481` |
| `maindec-8e-d0fc/maindec-8E-d0fc-d.pdf` | 406336 | `e36b62481499ee180ad9c42e0f148bf6fd8b65853a8cf03b041239442ab41128` |
| `maindec-8e-d0fc/maindec-8E-d0fc-pb` | 984 | `19309468c049df3d8e1854ebab75af090c9f76de75ca536b4baed844237d925a` |
| `maindec-8e-d0fc/maindec-8E-d0fc-pb.lbl` | 45 | `f11a277e3334bedc9661187e55104b692a7ea5999cee43da25783db38382eea8` |
| `maindec-8e-d0fc/maindec-8E-d0fc-pb.od` | 4920 | `f6ee97d6b136274539abe2eab3e0c5285a0f5ef871064125a5bf662038783b72` |
| `maindec-8e-d0gc/maindec-8E-d0gc-d.pdf` | 258389 | `f3c2a9deb2636aeca5402e7db2a525a64cda45be7c2a1b87330cfb21c14c0445` |
| `maindec-8e-d0gc/maindec-8E-d0gc-pb` | 671 | `6bda5b4f50d222c399a89ac1b7ec942a16d33f37bb3845b018a700ffc744e5e9` |
| `maindec-8e-d0gc/maindec-8E-d0gc-pb.od` | 3355 | `4f9d978992bd7a51cc709b10ae83b7c67258afadfeb4134a98971d9a06dc16e7` |
| `maindec-8e-d0hc/maindec-8E-d0hc-d.pdf` | 267016 | `a569d47e3a5ef1b994d43d8b801390923a545c2af2e0a7146c9344cc3e0744cf` |
| `maindec-8e-d0hc/maindec-8E-d0hc-pb` | 673 | `6083654c3e68fab51b58ce58a43d95595a7119a17fcabb90246f16b1f40128ac` |
| `maindec-8e-d0hc/maindec-8E-d0hc-pb.od` | 3365 | `4c657943573e89c6e00f001e7921b2f644a1acc2d043e0c2e906ded3e331b44d` |
| `maindec-8e-d0ib/maindec-8E-d0ib-d.pdf` | 1080156 | `abaa8fb3d2fb490a8efb8867c6cc665972a4e68d251844a7c377aeaf7b9f4a69` |
| `maindec-8e-d0ib/maindec-8E-d0ib-pb` | 3556 | `00c85cdbdefa76984259c19baab982d45322288a67aa3807fbd68f4d96fb9c10` |
| `maindec-8e-d0ib/maindec-8E-d0ib-pb.od` | 17780 | `d2589f7e15c001ae35473b4f6412855d755ab1aa1138964340ea40cadab44721` |
| `maindec-8e-d0jc/maindec-8E-d0jc-d.pdf` | 397253 | `a281e6105ec21bbe234a9d0c5dc5f79877ab24e10dcfb652275fb64b24ae0fdc` |
| `maindec-8e-d0jc/maindec-8E-d0jc-pb` | 909 | `15d1a406574da89c7748c2ddbfec8f580fe0bc11d761bcda53449097154be942` |
| `maindec-8e-d0jc/maindec-8E-d0jc-pb.lbl` | 51 | `ffb282bebaa055acaa5fc4dd3077301bd31800d17a48a7018b75e0047ecd8bb3` |
| `maindec-8e-d0jc/maindec-8E-d0jc-pb.od` | 4545 | `be8377ebf504e1de6556608a46555595fd3d52b11a9f64b4cf0590995f27ee9f` |
| `maindec-8e-d1aa/maindec-8E-d1aa-pb` | 1678 | `c9e95fca325050422c4d4a880b3a3369f4cadc94f5c20deff2293930e5a9f4be` |
| `maindec-8e-d1aa/maindec-8E-d1aa-pb.lbl` | 131 | `08271fedaf573b245642a5b05280d908efbaecf739c9d9c1b12229c555eed350` |
| `maindec-8e-d1aa/maindec-8E-d1aa-pb.od` | 10068 | `20312bbc870be81d89215a9e9a9351f120aafabb203bb64f3432d4516a01fdd1` |
| `maindec-8e-d1bc/MAINDEC-8E-D1B Note.txt` | 252 | `e7ca59e311d911e19c06dd517f51f7a83352b026e404fbd7005ab839c59edd0f` |
| `maindec-8e-d1bc/maindec-8E-d1bc-pb` | 2916 | `bc22201e4262fb6ab3a8e8b70e6440ff9b5f2f8e228f4be2a9a2b949825b8952` |
| `maindec-8e-d1bc/maindec-8E-d1bc-pb.lbl.jpg` | 297178 | `fe4cab36f3b79b9e66d5040c7cd2a7dab4a72de5c9e6c0523af0b28158c9c214` |
| `maindec-8e-d1bc/maindec-8E-d1bc-pb.od` | 14580 | `d8b805ff57597e0a8d912f92906168bf1cbd6ed298dc5c7c904a3e1a7f815179` |
| `maindec-8e-d1ec/maindec-8E-d1ec-d.pdf` | 789790 | `29a7c9c763eb938aed3f77faa71dcfaa2156db03cc57143e1e70aa19619c4792` |
| `maindec-8e-d1ec/maindec-8E-d1ec-pb` | 934 | `c0cbf9a8020fd1d198a3c2573e1a5e927d54b2469704e71b7f93d6f4da97177a` |
| `maindec-8e-d1ec/maindec-8E-d1ec-pb.lbl` | 64 | `efffbe6ddeb73e43afc0ab2801668835e1b5aeaf6df7b5da50a42bfc096aa4bb` |
| `maindec-8e-d1ec/maindec-8E-d1ec-pb.od` | 4670 | `ba7c57d3a90fa3f3e3333aaa73bd796b73aed89c5066366987c13e80f1bc83dc` |
| `maindec-8e-d1fb/maindec-8E-d1fb-d.pdf` | 2801213 | `b08aa987fc6fc1513077feea1d205096edb79dba2819944b50df6d88223d806b` |
| `maindec-8e-d1fb/maindec-8E-d1fb-pb` | 3352 | `5c64c5aa12c4270f93996764ece5dc42f421f51dfd5832b4f8a473159eebc7fd` |
| `maindec-8e-d1fb/maindec-8E-d1fb-pb.lbl` | 92 | `428ca5b1f18eaffdac35f67544082eb8aa1141ab4a7cb16a84db8fb5befa71d2` |
| `maindec-8e-d1fb/maindec-8E-d1fb-pb.od` | 16760 | `85a1fa374a8251ee1f660b568e3e984396661756546a7f4c21f8f3e59c29dc56` |
| `maindec-8e-d1ha/maindec-8E-d1ha-d.pdf` | 2175881 | `493322380418c5cd6f78fc6276dfd2893c816e84318abb2242e8217afd468103` |
| `maindec-8e-d1ha/maindec-8E-d1ha-pb` | 3714 | `14ae794f3af1c81b2a52dd3e1f686b36b9063f4e8e1c68abcd512b8eb4e447bc` |
| `maindec-8e-d1ha/maindec-8E-d1ha-pb.lbl` | 156 | `f4a61d2a7755d0f5ea32e103c3900891033465f240b185b5b023574898dc8c67` |
| `maindec-8e-d1ha/maindec-8E-d1ha-pb.od` | 22284 | `817f85fa29dff24e2a24523ae74115c37040f5b190eda05df9bf53aaa0dd55a0` |
| `maindec-8e-d1ha/maindec-8E-d1hb-d.pdf` | 3724729 | `d6fcbbe71cadf18a8bb7815eac35de2720473fa8503dcf334bacab8af8beaa0c` |
| `maindec-8e-d2ab/maindec-8E-d2ab-d-d.pdf` | 2318953 | `37f5d57018fe0ca527c1cd017ec45dc0d8f0f20ae0b5f45d7e9a4e790f3cd902` |
| `maindec-8e-d2ab/maindec-8E-d2ab-pb` | 6982 | `ec9b35a7ba516561390d8eac74aae06255a256f61d29f930285e1a670ccc6606` |
| `maindec-8e-d2ab/maindec-8E-d2ab-pb.lbl.jpg` | 305016 | `c0f3e825a68fb04d3cf7241df5982ec53edb5a1fc50ea34393c2e1e2ed07c68c` |
| `maindec-8e-d2ab/maindec-8E-d2ab-pb.od` | 34910 | `6ce044bb05e1d90d2531a0277b77d4d68fbd8477490c9fb2598baa79d6e06b53` |
| `maindec-8e-d2ca/maindec-8E-d2ca-pb` | 3620 | `43aac9411dd22e0ead5eb134ade5a3e9b06ddc5190c82a5f4fb367f49f958d29` |
| `maindec-8e-d2ca/maindec-8E-d2ca-pb.od` | 18100 | `b7c2b507399b994268c66634132d49dce5b94150e7198ee719d4aeb8d108cc78` |
