from .factories import MainBranchFactory, SubBranchFactory


def create_mainbranches(count):
    for i in range(count):
        MainBranchFactory.create()


def create_subbranches(count):
    for i in range(count):
        SubBranchFactory.create()
